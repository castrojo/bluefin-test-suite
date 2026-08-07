"""Behavioural contract tests for scripts/install-kde-webdriver.sh.

These tests *execute* the installer inside a hermetic sandbox instead of
grepping its source text. Text assertions cannot tell a live guard from a dead
one: the previous version of this file still passed when ``--host 0.0.0.0`` was
appended to ``ExecStart`` and when the source checkout ref was changed from the
pinned SHA to ``master``.

The sandbox gives the script:

* a fake ``PATH`` whose tools record their arguments and return scripted exit
  codes (``sudo``, ``dnf``, ``apt-get``, ``pacman``, ``rpm``, ``dpkg-query``,
  ``git``, ``cmake``, ``make``, ``systemctl``, ``plasmashell``, ``ruby`` and the
  upstream ``selenium-webdriver-at-spi-run`` entry point),
* a throwaway ``HOME`` so the generated systemd user unit can be parsed,
* a ``BASH_ENV`` preamble that overrides the ``source`` builtin for
  ``/etc/os-release`` only, making distro detection deterministic instead of
  inheriting whatever distro CI happens to run on.

Assertions are then made on observed behaviour: the resolved ``ExecStart`` and
``[Service]`` environment of the emitted unit, the exact ref handed to
``git fetch``/``git checkout``, and whether a skip branch actually
short-circuits the run.

Nothing here contacts invent.kde.org or any KDE mirror; this repo is read-only
toward all KDE properties.
"""

from __future__ import annotations

import configparser
import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "install-kde-webdriver.sh"

RUN_BIN_NAME = "selenium-webdriver-at-spi-run"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or not os.access("/etc/os-release", os.R_OK),
    reason="installer sandbox needs bash and a readable /etc/os-release to override",
)


def pinned_sha() -> str:
    """The SHA the installer declares, asserted against observed git calls."""
    match = re.search(
        r'^readonly SELENIUM_AT_SPI_SHA="([0-9a-f]{40})"$',
        SCRIPT.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert match, "installer must declare a 40-hex SELENIUM_AT_SPI_SHA"
    return match.group(1)


class InstallerRun:
    """Result of one sandboxed installer execution."""

    def __init__(self, proc: subprocess.CompletedProcess, home: Path, calls: Path):
        self.proc = proc
        self.home = home
        self._calls = calls

    @property
    def returncode(self) -> int:
        return self.proc.returncode

    @property
    def stdout(self) -> str:
        return self.proc.stdout

    @property
    def skip_reason(self) -> str | None:
        match = re.search(r"KDE_WEBDRIVER_SKIP=(.*)", self.stdout)
        return match.group(1).strip() if match else None

    def calls(self, tool: str) -> list[list[str]]:
        """Argv lists recorded for ``tool``, in invocation order."""
        recorded: list[list[str]] = []
        if not self._calls.exists():
            return recorded
        for line in self._calls.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            argv = line.split("\x1f")
            if argv[0] == tool:
                recorded.append(argv)
        return recorded

    @property
    def unit_path(self) -> Path:
        return self.home / ".config" / "systemd" / "user" / "kde-webdriver.service"

    def unit(self) -> configparser.ConfigParser:
        """Parse the generated systemd unit.

        ``strict=False`` because systemd allows repeated keys such as
        ``Environment=``; a strict parser would raise instead of letting the
        test inspect them.
        """
        assert self.unit_path.exists(), "installer did not write kde-webdriver.service"
        parser = configparser.ConfigParser(strict=False, interpolation=None)
        parser.optionxform = str
        parser.read_string(self.unit_path.read_text(encoding="utf-8"))
        return parser

    def service_environment(self) -> dict[str, str]:
        """``Environment=`` assignments from the unit's ``[Service]`` section."""
        env: dict[str, str] = {}
        in_service = False
        for raw in self.unit_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("["):
                in_service = line == "[Service]"
                continue
            if in_service and line.startswith("Environment="):
                for assignment in line[len("Environment=") :].split():
                    key, _, value = assignment.partition("=")
                    env[key] = value
        return env


def _write_tool(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(f"#!/bin/bash\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


_RECORD = (
    'printf "%s" "$(basename "$0")" >> "$CALL_LOG"\n'
    'for arg in "$@"; do printf "\\x1f%s" "$arg" >> "$CALL_LOG"; done\n'
    'printf "\\n" >> "$CALL_LOG"\n'
)

_PKG_BODY = _RECORD + textwrap.dedent(
    """
    for arg in "$@"; do
      case "$arg" in
        selenium-webdriver-at-spi*) exit "${PKG_SELENIUM_RC:-0}" ;;
      esac
    done
    exit 0
    """
)

# Emulate git honestly enough that the installer's own post-checkout
# `git rev-parse HEAD` comparison behaves as it would against real git.
_GIT_BODY = _RECORD + textwrap.dedent(
    """
    args=("$@")
    for arg in "${args[@]}"; do
      case "$arg" in
        clone)
          dest="${args[-1]}"
          mkdir -p "$dest"
          printf 'add_subdirectory(screenshotter)\\n' > "$dest/CMakeLists.txt"
          exit 0
          ;;
        checkout)
          printf '%s' "${args[-1]}" > "$CHECKED_OUT_REF"
          exit 0
          ;;
        rev-parse)
          cat "$CHECKED_OUT_REF"
          printf '\\n'
          exit 0
          ;;
      esac
    done
    exit 0
    """
)


def _build_sandbox(
    tmp_path: Path,
    *,
    distro_id: str,
    distro_id_like: str,
    plasma_version: str | None,
    packages_available: bool,
    run_bin_installed: bool,
) -> tuple[Path, Path, dict[str, str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    calls = tmp_path / "calls.log"

    # sudo stays transparent so the tool it fronts is the one recorded.
    _write_tool(bin_dir, "sudo", 'exec "$@"')

    for tool in ("cmake", "make", "systemctl", "ruby"):
        _write_tool(bin_dir, tool, _RECORD + "exit 0")

    for tool in ("dnf", "apt-get", "pacman"):
        _write_tool(bin_dir, tool, _PKG_BODY)

    # Version probes other than plasmashell must not leak the host's real
    # Plasma packages into the run.
    for tool in ("rpm", "dpkg-query"):
        _write_tool(bin_dir, tool, _RECORD + "exit 1")

    _write_tool(bin_dir, "git", _GIT_BODY)

    if plasma_version is not None:
        _write_tool(bin_dir, "plasmashell", _RECORD + f'echo "plasmashell {plasma_version}"')

    if run_bin_installed:
        _write_tool(bin_dir, RUN_BIN_NAME, _RECORD + "exit 0")

    # Deterministic distro detection: override `source` for /etc/os-release
    # only, leaving every other `source` call untouched.
    bash_env = tmp_path / "bash_env.sh"
    bash_env.write_text(
        "source() {\n"
        '  if [[ "$1" == /etc/os-release ]]; then\n'
        f'    ID="{distro_id}"\n'
        f'    ID_LIKE="{distro_id_like}"\n'
        "    return 0\n"
        "  fi\n"
        '  builtin source "$@"\n'
        "}\n",
        encoding="utf-8",
    )

    (tmp_path / "checked_out_ref").write_text("", encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}",
            "HOME": str(home),
            "CALL_LOG": str(calls),
            "CHECKED_OUT_REF": str(tmp_path / "checked_out_ref"),
            "BASH_ENV": str(bash_env),
            "PKG_SELENIUM_RC": "0" if packages_available else "1",
        }
    )
    for leaked in ("WAYLAND_DISPLAY", "DISPLAY", "FLASK_PORT"):
        env.pop(leaked, None)
    return home, calls, env


def run_installer(
    tmp_path: Path,
    *,
    distro_id: str = "fedora",
    distro_id_like: str = "",
    plasma_version: str | None = "6.2.4",
    packages_available: bool = True,
    run_bin_installed: bool = True,
    extra_env: dict[str, str] | None = None,
) -> InstallerRun:
    home, calls, env = _build_sandbox(
        tmp_path,
        distro_id=distro_id,
        distro_id_like=distro_id_like,
        plasma_version=plasma_version,
        packages_available=packages_available,
        run_bin_installed=run_bin_installed,
    )
    if extra_env:
        env.update(extra_env)

    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
        timeout=120,
    )
    return InstallerRun(proc, home, calls)


# ── source pin: the SHA must actually be the ref that gets checked out ────────


class TestSourcePin:
    def test_source_build_checks_out_the_pinned_sha(self, tmp_path):
        run = run_installer(tmp_path, packages_available=False)
        assert run.returncode == 0, run.proc.stderr

        checkouts = [call for call in run.calls("git") if "checkout" in call]
        assert checkouts, "source fallback must check out an explicit ref"
        assert [call[-1] for call in checkouts] == [pinned_sha()]

    def test_source_build_fetches_the_pinned_sha_not_a_branch(self, tmp_path):
        run = run_installer(tmp_path, packages_available=False)

        fetches = [call for call in run.calls("git") if "fetch" in call]
        assert fetches, "source fallback must fetch the pinned commit explicitly"
        for call in fetches:
            assert call[-1] == pinned_sha()
            assert "master" not in call and "main" not in call

    def test_source_build_clones_the_declared_upstream_url(self, tmp_path):
        run = run_installer(tmp_path, packages_available=False)

        clones = [call for call in run.calls("git") if "clone" in call]
        assert clones, "source fallback must clone before building"
        assert "https://github.com/KDE/selenium-webdriver-at-spi.git" in clones[0]

    def test_distro_packages_skip_the_source_clone_entirely(self, tmp_path):
        run = run_installer(tmp_path, packages_available=True)

        assert run.returncode == 0, run.proc.stderr
        assert not [call for call in run.calls("git") if "clone" in call]


# ── server posture: the emitted unit must bind loopback only ──────────────────


class TestServerUnitBindPosture:
    def test_execstart_is_the_bare_run_wrapper_with_no_bind_override(self, tmp_path):
        run = run_installer(tmp_path)
        exec_start = run.unit()["Service"]["ExecStart"]

        assert exec_start.endswith(f"{RUN_BIN_NAME} sleep infinity")
        for flag in ("--host", "--bind", "--listen", "0.0.0.0", "::"):
            assert flag not in exec_start, (
                f"ExecStart must not override the bind address: {exec_start!r}"
            )

    def test_service_environment_never_sets_a_non_loopback_host(self, tmp_path):
        env = run_installer(tmp_path).service_environment()

        for key in ("HOST", "FLASK_RUN_HOST", "SERVER_HOST", "BIND_ADDRESS"):
            assert env.get(key) in (None, "127.0.0.1", "localhost"), (
                f"server must bind loopback only, got {key}={env.get(key)!r}"
            )

    def test_flask_port_defaults_to_4723(self, tmp_path):
        assert run_installer(tmp_path).service_environment()["FLASK_PORT"] == "4723"

    def test_flask_port_honours_the_caller_override(self, tmp_path):
        run = run_installer(tmp_path, extra_env={"FLASK_PORT": "5599"})
        assert run.service_environment()["FLASK_PORT"] == "5599"

    def test_unit_is_bound_to_the_graphical_session(self, tmp_path):
        """A system-scope unit would run outside Wayland/AT-SPI and fail."""
        unit = run_installer(tmp_path).unit()

        assert unit["Unit"]["After"] == "graphical-session.target"
        assert unit["Install"]["WantedBy"] == "graphical-session.target"

    def test_unit_is_installed_and_enabled_in_the_user_scope(self, tmp_path):
        run = run_installer(tmp_path)

        assert run.unit_path.parent == run.home / ".config" / "systemd" / "user"
        enables = [call for call in run.calls("systemctl") if "enable" in call]
        assert enables and all("--user" in call for call in enables)

    def test_service_is_not_started_outside_a_graphical_session(self, tmp_path):
        run = run_installer(tmp_path)

        assert not [call for call in run.calls("systemctl") if "start" in call]
        assert "will start with next graphical session" in run.stdout


# ── skip paths: assert the branch fires, not that its text exists ─────────────


class TestSkipPaths:
    @pytest.mark.parametrize("version", ["5.20.5", "5.26.90", "4.14.38"])
    def test_plasma_below_baseline_skips_without_installing(self, tmp_path, version):
        run = run_installer(tmp_path, plasma_version=version)

        assert run.returncode == 0
        assert run.skip_reason is not None
        assert version in run.skip_reason
        assert not run.unit_path.exists(), "skip must short-circuit before install"
        assert run.calls("dnf") == []

    @pytest.mark.parametrize("version", ["5.27.11", "6.0.0", "6.2.4"])
    def test_supported_plasma_does_not_skip(self, tmp_path, version):
        run = run_installer(tmp_path, plasma_version=version)

        assert run.returncode == 0
        assert run.skip_reason is None
        assert run.unit_path.exists()

    def test_unsupported_distro_skips_before_building(self, tmp_path):
        run = run_installer(
            tmp_path,
            distro_id="gentoo",
            distro_id_like="",
            packages_available=False,
        )

        assert run.returncode == 0
        assert run.skip_reason is not None
        assert "unsupported distro" in run.skip_reason
        assert "gentoo" in run.skip_reason
        assert not run.unit_path.exists()
        assert not [call for call in run.calls("git") if "clone" in call]

    def test_missing_plasma_version_warns_but_continues(self, tmp_path):
        run = run_installer(tmp_path, plasma_version=None)

        assert run.returncode == 0
        assert run.skip_reason is None
        assert "could not determine Plasma version" in run.stdout
        assert run.unit_path.exists()

    def test_missing_run_binary_leaves_no_unit_and_still_exits_zero(self, tmp_path):
        run = run_installer(tmp_path, run_bin_installed=False)

        assert run.returncode == 0
        assert not run.unit_path.exists()
        assert f"{RUN_BIN_NAME} not found" in run.stdout

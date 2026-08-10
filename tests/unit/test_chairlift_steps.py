"""Unit tests for the homebrew suite's ChairLift steps and lane preconditions.

These cover the logic that is testable off-target: systemd property parsing,
the desktop `Exec=` realpath comparison, the bootc PolicyKit/helper contracts,
and the `before_all` preconditions that must FAIL the run rather than skip it.
"""

import sys
import types
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest


def _stub_modules() -> dict[str, types.ModuleType]:
    """Behave/dogtail/qecore stubs — none of them are installed in unit CI."""
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)

    qecore_stub = types.ModuleType("qecore")
    common_steps_stub = types.ModuleType("qecore.common_steps")
    common_steps_stub.__all__ = []
    sandbox_stub = types.ModuleType("qecore.sandbox")

    class _TestSandbox:  # noqa: D401 - stand-in for qecore.sandbox.TestSandbox
        def __init__(self, *args, **kwargs):
            self.applications = []

        def get_application(self, **kwargs):
            return types.SimpleNamespace(**kwargs)

    sandbox_stub.TestSandbox = _TestSandbox
    qecore_stub.common_steps = common_steps_stub
    qecore_stub.sandbox = sandbox_stub

    return {
        "behave": behave_stub,
        "qecore": qecore_stub,
        "qecore.common_steps": common_steps_stub,
        "qecore.sandbox": sandbox_stub,
    }


def _import(module_name: str):
    with patch.dict(sys.modules, _stub_modules()):
        sys.modules.pop(module_name, None)
        import importlib

        module = importlib.import_module(module_name)
    sys.modules.pop(module_name, None)
    return module


@pytest.fixture()
def steps():
    return _import("tests.homebrew.features.steps.chairlift_steps")


@pytest.fixture()
def environment():
    return _import("tests.homebrew.features.environment")


# ---------------------------------------------------------------------------
# brew-preinstall.service state — four properties, not just Result
# ---------------------------------------------------------------------------


def _show_output(**overrides: str) -> str:
    values = {
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "exited",
        "Result": "success",
    }
    values.update(overrides)
    return "".join(f"{key}={value}\n" for key, value in values.items())


def test_parse_properties_reads_key_value_lines(steps):
    parsed = steps._parse_properties("LoadState=loaded\nResult=success\n\nbroken\n")

    assert parsed == {"LoadState": "loaded", "Result": "success"}


def test_preinstall_state_pins_all_four_properties(steps):
    assert steps.PREINSTALL_STATE == {
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "exited",
        "Result": "success",
    }


def test_brew_preinstall_completed_passes_on_completed_oneshot(steps):
    with patch.object(
        steps, "_run", return_value=CompletedProcess([], 0, _show_output(), "")
    ):
        steps.brew_preinstall_completed(None)


@pytest.mark.parametrize(
    ("overrides", "expected_fragment"),
    [
        # A unit that never ran still reports Result=success — the exact
        # false-positive the single-property assertion allowed.
        ({"ActiveState": "inactive", "SubState": "dead"}, "inactive"),
        ({"LoadState": "not-found"}, "not-found"),
        ({"SubState": "running"}, "running"),
        ({"Result": "exit-code"}, "exit-code"),
    ],
)
def test_brew_preinstall_completed_fails_on_bad_state(steps, overrides, expected_fragment):
    with patch.object(
        steps,
        "_run",
        return_value=CompletedProcess([], 0, _show_output(**overrides), ""),
    ):
        with pytest.raises(AssertionError) as error:
            steps.brew_preinstall_completed(None)

    assert expected_fragment in str(error.value)


def test_brew_preinstall_completed_fails_when_systemctl_fails(steps):
    with patch.object(
        steps,
        "_run",
        return_value=CompletedProcess([], 1, "", "Failed to connect to bus"),
    ):
        with pytest.raises(AssertionError, match="Failed to connect to bus"):
            steps.brew_preinstall_completed(None)


# ---------------------------------------------------------------------------
# Desktop Exec= comparison via realpath (/home vs /var/home spellings)
# ---------------------------------------------------------------------------


@pytest.fixture()
def symlinked_prefix(tmp_path: Path) -> tuple[Path, Path]:
    """Mimic a bootc image where /home is a symlink to /var/home."""
    real_bin = tmp_path / "var/home/linuxbrew/.linuxbrew/bin"
    real_bin.mkdir(parents=True)
    (real_bin / "chairlift-wrapper").write_text("#!/bin/sh\n", encoding="utf-8")
    (tmp_path / "home").symlink_to(tmp_path / "var/home")
    return tmp_path / "home/linuxbrew/.linuxbrew/bin", real_bin


def _write_desktop(tmp_path: Path, exec_line: str) -> Path:
    desktop = tmp_path / "org.frostyard.ChairLift.desktop"
    desktop.write_text(
        "[Desktop Entry]\nName=ChairLift\n" f"Exec={exec_line}\nType=Application\n",
        encoding="utf-8",
    )
    return desktop


def test_desktop_exec_accepts_symlinked_spelling(steps, tmp_path, symlinked_prefix):
    symlinked_bin, real_bin = symlinked_prefix
    desktop = _write_desktop(tmp_path, str(symlinked_bin / "chairlift-wrapper"))

    with patch.object(steps, "DESKTOP_FILE", desktop), patch.object(
        steps, "CHAIRLIFT_WRAPPER", str(real_bin / "chairlift-wrapper")
    ):
        steps.chairlift_desktop_entry_launches_wrapper(None)


def test_desktop_exec_rejects_other_binary(steps, tmp_path, symlinked_prefix):
    _, real_bin = symlinked_prefix
    desktop = _write_desktop(tmp_path, str(real_bin / "chairlift"))

    with patch.object(steps, "DESKTOP_FILE", desktop), patch.object(
        steps, "CHAIRLIFT_WRAPPER", str(real_bin / "chairlift-wrapper")
    ):
        with pytest.raises(AssertionError, match="Expected Exec to resolve to"):
            steps.chairlift_desktop_entry_launches_wrapper(None)


def test_desktop_exec_rejects_extra_arguments(steps, tmp_path, symlinked_prefix):
    _, real_bin = symlinked_prefix
    desktop = _write_desktop(tmp_path, f"{real_bin / 'chairlift-wrapper'} --update-now")

    with patch.object(steps, "DESKTOP_FILE", desktop), patch.object(
        steps, "CHAIRLIFT_WRAPPER", str(real_bin / "chairlift-wrapper")
    ):
        with pytest.raises(AssertionError, match="no extra arguments"):
            steps.chairlift_desktop_entry_launches_wrapper(None)


# ---------------------------------------------------------------------------
# bootc staging: PolicyKit defaults + single download-only exec
# ---------------------------------------------------------------------------


POLICY_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<policyconfig>
  <action id="org.frostyard.ChairLift.bootc.stage">
    <defaults>
      <allow_any>{allow_any}</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">{exec_path}</annotate>
  </action>
</policyconfig>
"""


def _write_policy(tmp_path: Path, *, allow_any="auth_admin", exec_path="/usr/libexec/bootc-update-stage") -> Path:
    policy = tmp_path / "org.frostyard.ChairLift.bootc.policy"
    policy.write_text(
        POLICY_TEMPLATE.format(allow_any=allow_any, exec_path=exec_path), encoding="utf-8"
    )
    return policy


def test_policykit_action_requires_admin(steps, tmp_path):
    with patch.object(steps, "POLICY_FILE", _write_policy(tmp_path)):
        steps.chairlift_bootc_policykit_requires_admin(None)


def test_policykit_action_rejects_passwordless_default(steps, tmp_path):
    with patch.object(steps, "POLICY_FILE", _write_policy(tmp_path, allow_any="yes")):
        with pytest.raises(AssertionError, match="Unexpected PolicyKit defaults"):
            steps.chairlift_bootc_policykit_requires_admin(None)


def test_policykit_action_rejects_other_exec_path(steps, tmp_path):
    policy = _write_policy(tmp_path, exec_path="/usr/bin/bootc")
    with patch.object(steps, "POLICY_FILE", policy):
        with pytest.raises(AssertionError, match="Expected exec.path"):
            steps.chairlift_bootc_policykit_requires_admin(None)


@pytest.mark.parametrize(
    ("body", "raises"),
    [
        ("#!/usr/bin/bash\nset -euo pipefail\nexec /usr/bin/bootc upgrade --download-only\n", False),
        ("#!/usr/bin/bash\nexec /usr/bin/bootc upgrade\n", True),
        ('#!/usr/bin/bash\nexec /usr/bin/bootc upgrade --download-only "$@"\n', True),
        (
            "#!/usr/bin/bash\nexec /usr/bin/bootc upgrade --download-only\n"
            "exec /usr/bin/bootc upgrade --apply\n",
            True,
        ),
    ],
)
def test_bootc_helper_download_only(steps, tmp_path, body, raises):
    helper = tmp_path / "bootc-update-stage"
    helper.write_text(body, encoding="utf-8")

    with patch.object(steps, "BOOTC_HELPER", helper):
        if raises:
            with pytest.raises(AssertionError):
                steps.chairlift_bootc_helper_download_only(None)
        else:
            steps.chairlift_bootc_helper_download_only(None)


# ---------------------------------------------------------------------------
# Lane preconditions FAIL the run; they never become a skip
# ---------------------------------------------------------------------------


def test_runtime_dir_is_pinned_to_uid_1000(environment):
    assert environment.USER_RUNTIME_DIR == "/run/user/1000"


def test_pin_user_runtime_dir_sets_unset_value(environment):
    with patch.dict("os.environ", {}, clear=True):
        environment._pin_user_runtime_dir()

        import os

        assert os.environ["XDG_RUNTIME_DIR"] == "/run/user/1000"


def test_pin_user_runtime_dir_rejects_other_value(environment):
    with patch.dict("os.environ", {"XDG_RUNTIME_DIR": "/run/user/1001"}, clear=True):
        with pytest.raises(environment.HomebrewLaneError, match="XDG_RUNTIME_DIR=/run/user/1000"):
            environment._pin_user_runtime_dir()


def test_require_user_manager_raises_when_socket_unreachable(environment):
    with patch.object(
        environment.subprocess,
        "run",
        return_value=CompletedProcess([], 1, "", "Failed to connect to bus: No such file"),
    ):
        with pytest.raises(environment.HomebrewLaneError, match="user manager unreachable"):
            environment._require_user_manager()


def test_require_user_manager_passes_when_reachable(environment):
    with patch.object(
        environment.subprocess, "run", return_value=CompletedProcess([], 0, "257\n", "")
    ):
        environment._require_user_manager()


def test_start_brew_preinstall_raises_on_failure(environment):
    with patch.object(
        environment.subprocess,
        "run",
        return_value=CompletedProcess([], 1, "", "Unit brew-preinstall.service not found."),
    ):
        with pytest.raises(environment.HomebrewLaneError, match="failed to start"):
            environment._start_brew_preinstall()


def test_before_all_raises_instead_of_recording_failed_setup(environment):
    context = types.SimpleNamespace()

    with patch.object(environment, "_pin_user_runtime_dir"), patch.object(
        environment,
        "_require_user_manager",
        side_effect=environment.HomebrewLaneError("no user manager"),
    ):
        with pytest.raises(environment.HomebrewLaneError):
            environment.before_all(context)

    assert not hasattr(context, "failed_setup")
    assert context.lane_ready is False


# ---------------------------------------------------------------------------
# Source-level invariants (regression guards for skipped-green setups)
# ---------------------------------------------------------------------------


def _environment_source() -> str:
    return (
        Path(__file__).resolve().parents[1] / "homebrew/features/environment.py"
    ).read_text(encoding="utf-8")


def test_environment_never_skips_on_setup_failure():
    source = _environment_source()

    assert "failed_setup" not in source
    # skip_quarantine (tag-driven) is the only sanctioned skip in this suite.
    assert "scenario.skip(" not in source


def test_environment_registers_lowercase_a11y_root():
    source = _environment_source()

    assert 'a11y_app_name="chairlift"' in source
    assert 'a11y_app_name="ChairLift"' not in source

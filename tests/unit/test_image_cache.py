"""Unit tests for tests/shared/image_cache.py (#501)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.shared import image_cache
from tests.shared.image_cache import (
    REQUIRES_CACHED_IMAGE_TAG,
    _looks_like_image_ref,
    images_required_by,
    skip_when_image_not_cached,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLBOX_IMAGE = "registry.fedoraproject.org/fedora-toolbox:latest"


# ── helpers ───────────────────────────────────────────────────────────────────


class _FakeStep:
    def __init__(self, name: str):
        self.name = name


class _FakeScenario:
    """Minimal behave Scenario stand-in for unit testing."""

    def __init__(self, tags=None, steps=None, *, skip_raises=False):
        self.tags = list(tags or [])
        self.effective_tags = self.tags
        self.steps = [_FakeStep(text) for text in (steps or [])]
        self.skip_raises = skip_raises
        self.skip_message: str | None = None
        self.skipped = False

    def skip(self, message: str | None = None) -> None:
        if self.skip_raises and message is not None:
            raise TypeError("skip() takes no arguments")
        self.skipped = True
        self.skip_message = message


class _FakeSSH:
    """Stand-in for image_cache._ssh_returncode, recording probe commands."""

    def __init__(self, cached=(), raises=None):
        self.cached = set(cached)
        self.raises = raises
        self.commands: list[str] = []

    def __call__(self, context, command, timeout=30):
        self.commands.append(command)
        if self.raises is not None:
            raise self.raises
        image = command.rsplit(" ", 1)[-1].strip("'\"")
        return 0 if image in self.cached else 1


@pytest.fixture
def fake_ssh(monkeypatch):
    """Install a fake SSH probe; returns a factory the test configures."""

    def _install(cached=(), raises=None):
        ssh = _FakeSSH(cached=cached, raises=raises)
        monkeypatch.setattr(image_cache, "_ssh_returncode", ssh)
        return ssh

    return _install


def _distrobox_scenario(tags=("requires_cached_image",), image=TOOLBOX_IMAGE):
    return _FakeScenario(
        tags=list(tags),
        steps=[
            f'DX distrobox "test-box" can be created from "{image}"',
            'DX distrobox "test-box" installs package "htop"',
            'DX distrobox "test-box" exports "/usr/bin/htop" to the host',
        ],
    )


# ── _looks_like_image_ref ─────────────────────────────────────────────────────


class TestLooksLikeImageRef:
    @pytest.mark.parametrize(
        "token",
        [
            TOOLBOX_IMAGE,
            "ghcr.io/ublue-os/bluefin-dx:latest",
            "localhost/my-image:dev",
            "registry.example.com:5000/team/app:1.2.3",
            "quay.io/fedora/fedora@sha256:abc123",
        ],
    )
    def test_accepts_registry_qualified_refs(self, token):
        assert _looks_like_image_ref(token) is True

    @pytest.mark.parametrize(
        "token",
        [
            "",
            "test-box",
            "htop",
            "/usr/bin/htop",
            "~/.local/bin",
            "fedora:latest",  # no registry: resolution depends on registries.conf
            "ghcr.io/ublue-os/bluefin-dx",  # no tag or digest
            "registry.example.com/some image:latest",  # whitespace
        ],
    )
    def test_rejects_everything_else(self, token):
        assert _looks_like_image_ref(token) is False


# ── images_required_by ────────────────────────────────────────────────────────


class TestImagesRequiredBy:
    def test_extracts_the_image_from_step_text(self):
        assert images_required_by(_distrobox_scenario()) == [TOOLBOX_IMAGE]

    def test_collapses_duplicate_references(self):
        scenario = _FakeScenario(
            steps=[
                f'DX distrobox "a" can be created from "{TOOLBOX_IMAGE}"',
                f'DX distrobox "b" can be created from "{TOOLBOX_IMAGE}"',
            ]
        )
        assert images_required_by(scenario) == [TOOLBOX_IMAGE]

    def test_preserves_order_of_distinct_images(self):
        other = "ghcr.io/ublue-os/bluefin-dx:latest"
        scenario = _FakeScenario(
            steps=[
                f'DX distrobox "a" can be created from "{TOOLBOX_IMAGE}"',
                f'DX distrobox "b" can be created from "{other}"',
            ]
        )
        assert images_required_by(scenario) == [TOOLBOX_IMAGE, other]

    def test_ignores_non_image_arguments(self):
        scenario = _FakeScenario(
            steps=['DX distrobox "test-box" exports "/usr/bin/htop" to the host']
        )
        assert images_required_by(scenario) == []

    def test_tolerates_a_scenario_without_steps(self):
        assert images_required_by(_FakeScenario()) == []


# ── skip_when_image_not_cached ────────────────────────────────────────────────


class TestSkipWhenImageNotCached:
    def test_untagged_scenario_is_never_probed(self, fake_ssh):
        ssh = fake_ssh(cached=())
        scenario = _distrobox_scenario(tags=("dx", "distrobox"))

        assert skip_when_image_not_cached(None, scenario) is False
        assert not scenario.skipped
        assert ssh.commands == []

    def test_runs_when_the_image_is_cached(self, fake_ssh):
        fake_ssh(cached=(TOOLBOX_IMAGE,))
        scenario = _distrobox_scenario()

        assert skip_when_image_not_cached(None, scenario) is False
        assert not scenario.skipped

    def test_skips_when_the_image_is_absent(self, fake_ssh):
        fake_ssh(cached=())
        scenario = _distrobox_scenario()

        assert skip_when_image_not_cached(None, scenario) is True
        assert scenario.skipped
        assert TOOLBOX_IMAGE in scenario.skip_message
        assert REQUIRES_CACHED_IMAGE_TAG in scenario.skip_message

    def test_probes_each_distinct_image_once(self, fake_ssh):
        ssh = fake_ssh(cached=(TOOLBOX_IMAGE,))
        skip_when_image_not_cached(None, _distrobox_scenario())

        assert ssh.commands == [f"podman image exists {TOOLBOX_IMAGE}"]

    def test_skips_when_the_tag_names_no_image(self, fake_ssh):
        fake_ssh(cached=(TOOLBOX_IMAGE,))
        scenario = _FakeScenario(
            tags=[REQUIRES_CACHED_IMAGE_TAG],
            steps=['DX distrobox "test-box" installs package "htop"'],
        )

        assert skip_when_image_not_cached(None, scenario) is True
        assert "no image reference found" in scenario.skip_message

    def test_skip_message_is_optional_for_older_behave(self, fake_ssh):
        fake_ssh(cached=())
        scenario = _distrobox_scenario()
        scenario.skip_raises = True

        assert skip_when_image_not_cached(None, scenario) is True
        assert scenario.skipped


class _FakeCompletedProcess:
    def __init__(self, returncode):
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


def _ssh_context():
    """Context carrying the connection details resolve_ssh_details() reads."""
    context = MagicMock()
    context.ssh_key = "/tmp/key"
    context.vm_ip = "192.0.2.10"
    context.ssh_user = "bluefin-test"
    context.ssh_port = "2222"
    context.config.userdata = {}
    return context


class TestImageIsCached:
    def _patch_subprocess(self, monkeypatch, result):
        calls: list[list[str]] = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if isinstance(result, BaseException):
                raise result
            return _FakeCompletedProcess(result)

        monkeypatch.setattr(image_cache.subprocess, "run", fake_run)
        return calls

    def test_true_when_podman_image_exists_succeeds(self, monkeypatch):
        self._patch_subprocess(monkeypatch, 0)
        assert image_cache.image_is_cached(_ssh_context(), TOOLBOX_IMAGE) is True

    def test_false_when_podman_image_exists_fails(self, monkeypatch):
        self._patch_subprocess(monkeypatch, 1)
        assert image_cache.image_is_cached(_ssh_context(), TOOLBOX_IMAGE) is False

    def test_false_when_the_dut_is_unreachable(self, monkeypatch):
        self._patch_subprocess(monkeypatch, OSError("no route to host"))
        assert image_cache.image_is_cached(_ssh_context(), TOOLBOX_IMAGE) is False

    def test_false_when_the_probe_times_out(self, monkeypatch):
        self._patch_subprocess(monkeypatch, subprocess.TimeoutExpired("ssh", 30))
        assert image_cache.image_is_cached(_ssh_context(), TOOLBOX_IMAGE) is False

    def test_probe_never_contacts_a_registry(self, monkeypatch):
        """`podman image exists` is local-only — a pulling probe would defeat the gate."""
        calls = self._patch_subprocess(monkeypatch, 0)
        image_cache.image_is_cached(_ssh_context(), TOOLBOX_IMAGE)

        remote_command = calls[0][-1]
        assert remote_command == f"podman image exists {TOOLBOX_IMAGE}"
        assert "pull" not in remote_command

    def test_probe_uses_the_resolved_connection_details(self, monkeypatch):
        calls = self._patch_subprocess(monkeypatch, 0)
        image_cache.image_is_cached(_ssh_context(), TOOLBOX_IMAGE)

        argv = calls[0]
        assert argv[0] == "ssh"
        assert "bluefin-test@192.0.2.10" in argv
        assert argv[argv.index("-i") + 1] == "/tmp/key"
        assert argv[argv.index("-p") + 1] == "2222"

    def test_probe_does_not_mutate_context_command_state(self, monkeypatch):
        """The gate runs before before_scenario resets state; it must not smear output."""
        self._patch_subprocess(monkeypatch, 0)
        context = _ssh_context()
        context.command_stdout = "sentinel"
        context.ssh_rc = 99

        image_cache.image_is_cached(context, TOOLBOX_IMAGE)

        assert context.command_stdout == "sentinel"
        assert context.ssh_rc == 99


def test_gate_does_not_import_the_shared_ssh_step_library():
    """Importing tests/shared/ssh_steps.py from a hook would raise AmbiguousStep.

    It registers `SSH command return code is "{code}"` and
    `Last command output contains "{text}"`, which tests/dx/features/steps/steps.py
    also defines. A DX before_scenario hook that pulled it in would take the
    whole suite down, so the probe must stay on tests/shared/ssh_config.py.
    """
    source = (REPO_ROOT / "tests/shared/image_cache.py").read_text(encoding="utf-8")
    importing_lines = [
        line
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from ")) and "ssh_steps" in line
    ]
    assert not importing_lines, (
        f"image_cache.py must not import ssh_steps: {importing_lines}"
    )


# ── the tag must never be inert in the real feature files ─────────────────────


_SCENARIO_BLOCK = re.compile(
    r"^[ \t]*(@[^\n]*\n[ \t]*)*@[^\n]*\brequires_cached_image\b[^\n]*\n"
    r"(?P<body>(?:[ \t]*(?:Scenario|Scenario Outline):[^\n]*\n)(?:(?![ \t]*@|[ \t]*Scenario).*\n)*)",
    re.MULTILINE,
)


def _tagged_scenario_bodies():
    for feature in sorted(REPO_ROOT.glob("tests/*/features/**/*.feature")):
        text = feature.read_text(encoding="utf-8")
        if REQUIRES_CACHED_IMAGE_TAG not in text:
            continue
        for match in _SCENARIO_BLOCK.finditer(text):
            yield feature, match.group("body")


def test_every_tagged_scenario_names_an_image():
    """A @requires_cached_image scenario whose steps name no image would skip forever.

    The runtime gate reads the image out of the scenario's own steps, so a tag
    applied to a scenario that never names one is an authoring error. Catching
    it here keeps it out of CI, where it would look like an infra skip.
    """
    bodies = list(_tagged_scenario_bodies())
    assert bodies, "expected at least one @requires_cached_image scenario"

    for feature, body in bodies:
        scenario = _FakeScenario(steps=body.splitlines())
        assert images_required_by(scenario), (
            f"{feature.relative_to(REPO_ROOT)}: @{REQUIRES_CACHED_IMAGE_TAG} scenario "
            f"names no registry-qualified image:\n{body}"
        )


def test_tagged_scenarios_are_not_masked_by_a_non_runnable_tag():
    """The gate only runs for scenarios the runtime actually reaches.

    tests/shared/quarantine.py skips @quarantine/@hardware_blocked/@future/@pending
    before this gate ever sees the scenario, so pairing @requires_cached_image
    with one of them makes it inert — the masking trap documented in
    docs/skills/test-authoring/suite-map/SKILL.md.
    """
    from tests.shared.quarantine import _SKIP_TAGS

    for feature in sorted(REPO_ROOT.glob("tests/*/features/**/*.feature")):
        for line in feature.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith("@") or REQUIRES_CACHED_IMAGE_TAG not in stripped:
                continue
            tags = {tag.lstrip("@") for tag in stripped.split()}
            masking = tags.intersection(_SKIP_TAGS)
            assert not masking, (
                f"{feature.relative_to(REPO_ROOT)}: @{REQUIRES_CACHED_IMAGE_TAG} is masked "
                f"by {sorted(masking)} — the gate never runs for this scenario"
            )

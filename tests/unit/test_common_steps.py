"""Unit tests for tests/common features step and environment helpers."""
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

def _import_common_steps():
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    ssh_steps_stub = types.ModuleType("tests.shared.ssh_steps")
    ssh_steps_stub.run_ssh = lambda *a, **kw: ("", 0)
    _ensure_tests_shared_package()
    sys.modules["tests.shared.ssh_steps"] = ssh_steps_stub

    for key in list(sys.modules):
        if "common.features.steps.steps" in key:
            del sys.modules[key]

    import tests.common.features.steps.steps as m  # noqa: PLC0415
    return m


def _ctx(**attrs):
    ctx = MagicMock()
    for k, v in attrs.items():
        setattr(ctx, k, v)
    return ctx


_ENVIRONMENT_STUB_KEYS = [
    "tests.shared.ssh_steps",
    "tests.shared.quarantine",
    "tests.shared.timing",
]


def _ensure_tests_shared_package():
    """Make sure `tests.shared` in sys.modules is the real package.

    `before_scenario` imports `tests.shared.quarantine` lazily, at call time
    rather than at module import. If `tests.shared` has been replaced by a
    plain `ModuleType` it carries no `__path__`, so that submodule import
    raises `ModuleNotFoundError: 'tests.shared' is not a package` — but only
    when this file runs in isolation, since a real import elsewhere in the
    suite otherwise leaves the genuine package cached.
    """
    cached = sys.modules.get("tests.shared")
    if cached is not None and not hasattr(cached, "__path__"):
        # A previous helper installed a non-package stub; drop it so the
        # import below resolves the real package from disk.
        del sys.modules["tests.shared"]

    import tests.shared  # noqa: PLC0415

    sys.modules["tests.shared"] = tests.shared

def _import_common_environment(*, run_ssh_returncode=0):
    ssh_steps_stub = types.ModuleType("tests.shared.ssh_steps")

    def _run_ssh(context, cmd, timeout=60):
        context.command_stdout = ""
        context.last_command_output = ""
        context.ssh_rc = run_ssh_returncode
        context.last_ssh_result = None
        return "", run_ssh_returncode

    ssh_steps_stub.run_ssh = _run_ssh

    # Save originals before overwriting — restored in teardown via the sentinel
    # dict stored on the returned module so callers can clean up.
    _saved = {k: sys.modules.get(k) for k in _ENVIRONMENT_STUB_KEYS}

    _ensure_tests_shared_package()
    sys.modules["tests.shared.ssh_steps"] = ssh_steps_stub

    quarantine_stub = types.ModuleType("tests.shared.quarantine")
    quarantine_stub.skip_quarantine = lambda scenario: False
    sys.modules["tests.shared.quarantine"] = quarantine_stub

    timing_stub = types.ModuleType("tests.shared.timing")
    timing_stub.record_start = lambda context: None
    timing_stub.record_end = lambda context, scenario: None
    sys.modules["tests.shared.timing"] = timing_stub

    for key in list(sys.modules):
        if key.endswith("common.features.environment"):
            del sys.modules[key]

    import tests.common.features.environment as m  # noqa: PLC0415

    # Restore sys.modules so the stub does not shadow the real timing module
    # for subsequent test files (e.g. test_timing.py).
    for k, v in _saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v

    return m


class _Scenario:
    def __init__(self, tags):
        self.tags = list(tags)
        self.effective_tags = list(tags)
        self.skip_message = None

    def skip(self, message=None):
        self.skip_message = message


# ---------------------------------------------------------------------------
# last_command_exits_with_non_zero_status
# ---------------------------------------------------------------------------

class TestLastCommandExitsWithNonZeroStatus:
    def test_passes_when_rc_is_nonzero(self):
        m = _import_common_steps()
        ctx = _ctx(ssh_rc=1, last_ssh_result=None)
        m.last_command_exits_with_non_zero_status(ctx)  # should not raise

    def test_passes_when_rc_is_large_nonzero(self):
        m = _import_common_steps()
        ctx = _ctx(ssh_rc=127, last_ssh_result=None)
        m.last_command_exits_with_non_zero_status(ctx)  # should not raise

    def test_raises_when_rc_is_zero(self):
        m = _import_common_steps()
        ctx = _ctx(ssh_rc=0, last_ssh_result=None)
        with pytest.raises(AssertionError, match="non-zero"):
            m.last_command_exits_with_non_zero_status(ctx)

    def test_raises_when_rc_is_none(self):
        m = _import_common_steps()
        ctx = _ctx(ssh_rc=None, last_ssh_result=None)
        with pytest.raises(AssertionError):
            m.last_command_exits_with_non_zero_status(ctx)

    def test_raises_when_ssh_rc_missing(self):
        m = _import_common_steps()
        ctx = MagicMock(spec=[])  # no attributes at all
        with pytest.raises(AssertionError):
            m.last_command_exits_with_non_zero_status(ctx)

    def test_includes_stdout_in_error_message(self):
        m = _import_common_steps()
        last_result = MagicMock()
        last_result.stderr = ""
        last_result.stdout = "unexpected success output"
        ctx = _ctx(ssh_rc=0, last_ssh_result=last_result)
        with pytest.raises(AssertionError, match="unexpected success output"):
            m.last_command_exits_with_non_zero_status(ctx)

    def test_includes_stderr_in_error_message(self):
        m = _import_common_steps()
        last_result = MagicMock()
        last_result.stderr = "something went wrong but rc=0"
        last_result.stdout = ""
        ctx = _ctx(ssh_rc=0, last_ssh_result=last_result)
        with pytest.raises(AssertionError, match="something went wrong"):
            m.last_command_exits_with_non_zero_status(ctx)


class TestCommonEnvironmentRequiresBrew:
    def test_skips_requires_brew_when_brew_is_missing(self):
        m = _import_common_environment(run_ssh_returncode=1)
        context = _ctx(is_bluefin_image=True, has_brew=None)
        scenario = _Scenario(["requires_brew"])

        m.before_scenario(context, scenario)

        assert scenario.skip_message == "Homebrew not present on this image"
        assert context.has_brew is False

    def test_allows_requires_brew_when_brew_is_present(self):
        m = _import_common_environment(run_ssh_returncode=0)
        context = _ctx(is_bluefin_image=True, has_brew=None)
        scenario = _Scenario(["requires_brew"])

        m.before_scenario(context, scenario)

        assert scenario.skip_message is None
        assert context.has_brew is True


# ---------------------------------------------------------------------------
# _is_dakota_image / @dakota_only gating
# ---------------------------------------------------------------------------

class TestIsDakotaImage:
    @pytest.mark.parametrize(
        "image",
        [
            "ghcr.io/projectbluefin/dakota:testing",
            "ghcr.io/projectbluefin/dakota",
            "DAKOTA:latest",
            "ghcr.io/projectbluefin/dakota@sha256:abc123",
        ],
    )
    def test_matches_dakota_images(self, image):
        m = _import_common_environment()
        assert m._is_dakota_image(image) is True

    @pytest.mark.parametrize(
        "image",
        [
            "ghcr.io/projectbluefin/bluefin:testing",
            "ghcr.io/projectbluefin/bluefin-lts:latest",
            "ghcr.io/ublue-os/bazzite:stable",
            "",
        ],
    )
    def test_rejects_non_dakota_images(self, image):
        m = _import_common_environment()
        assert m._is_dakota_image(image) is False

    def test_org_name_alone_does_not_match(self):
        """Only the image name is inspected, so a dakota-named org cannot match."""
        m = _import_common_environment()
        assert m._is_dakota_image("ghcr.io/dakota/bluefin:testing") is False


class TestCommonEnvironmentDakotaOnly:
    def test_skips_dakota_only_on_non_dakota_image(self):
        m = _import_common_environment()
        context = _ctx(is_bluefin_image=True, is_dakota_image=False)
        scenario = _Scenario(["dakota_only"])

        m.before_scenario(context, scenario)

        assert "Skipping @dakota_only scenario" in scenario.skip_message

    def test_allows_dakota_only_on_dakota_image(self):
        m = _import_common_environment()
        context = _ctx(is_bluefin_image=True, is_dakota_image=True, has_brew=True)
        scenario = _Scenario(["dakota_only"])

        m.before_scenario(context, scenario)

        assert scenario.skip_message is None


class TestCommonEnvironmentRequiresBctl:
    def test_skips_requires_bctl_when_bctl_is_missing(self):
        m = _import_common_environment(run_ssh_returncode=1)
        context = _ctx(is_bluefin_image=True, has_brew=True, has_bctl=None)
        scenario = _Scenario(["requires_bctl"])

        m.before_scenario(context, scenario)

        assert scenario.skip_message == "bluefinctl (bctl) not present on this image"
        assert context.has_bctl is False

    def test_allows_requires_bctl_when_bctl_is_present(self):
        m = _import_common_environment(run_ssh_returncode=0)
        context = _ctx(is_bluefin_image=True, has_brew=True, has_bctl=None)
        scenario = _Scenario(["requires_bctl"])

        m.before_scenario(context, scenario)

        assert scenario.skip_message is None
        assert context.has_bctl is True


class TestCommonEnvironmentDevmodeCleanup:
    def test_disables_devmode_after_a_tagged_scenario(self):
        m = _import_common_environment(run_ssh_returncode=0)
        calls = []
        m.run_ssh = lambda context, cmd, **kw: (calls.append(cmd), ("", 0))[1]
        context = _ctx()
        scenario = _Scenario(["devmode_cleanup"])
        scenario.status = "passed"

        m.after_scenario(context, scenario)

        assert calls == ["bctl devmode --disable"]

    def test_skips_cleanup_for_untagged_scenarios(self):
        m = _import_common_environment(run_ssh_returncode=0)
        calls = []
        m.run_ssh = lambda context, cmd, **kw: (calls.append(cmd), ("", 0))[1]
        context = _ctx()
        scenario = _Scenario(["requires_bctl"])
        scenario.status = "passed"

        m.after_scenario(context, scenario)

        assert calls == []

    def test_skips_cleanup_when_scenario_was_skipped(self):
        m = _import_common_environment(run_ssh_returncode=0)
        calls = []
        m.run_ssh = lambda context, cmd, **kw: (calls.append(cmd), ("", 0))[1]
        context = _ctx()
        scenario = _Scenario(["devmode_cleanup"])
        scenario.status = "skipped"

        m.after_scenario(context, scenario)

        assert calls == []

    def test_cleanup_failure_does_not_mask_the_real_failure(self):
        m = _import_common_environment(run_ssh_returncode=0)

        def _boom(context, cmd, **kw):
            raise RuntimeError("ssh transport died")

        m.run_ssh = _boom
        context = _ctx()
        scenario = _Scenario(["devmode_cleanup"])
        scenario.status = "failed"

        m.after_scenario(context, scenario)  # should not raise

"""Unit tests for tests/common/features/steps/steps.py step assertion helpers."""
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
    sys.modules["tests.shared"] = sys.modules.get("tests.shared", types.ModuleType("tests.shared"))
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

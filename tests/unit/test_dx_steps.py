"""Unit tests for tests/dx/features/steps/steps.py assertion helpers."""
import sys
import types
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

def _import_dx_steps():
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    qecore_stub = types.ModuleType("qecore")
    qecore_common_stub = types.ModuleType("qecore.common_steps")
    sys.modules["qecore"] = qecore_stub
    sys.modules["qecore.common_steps"] = qecore_common_stub

    for key in list(sys.modules):
        if "dx.features.steps.steps" in key:
            del sys.modules[key]

    import tests.dx.features.steps.steps as m  # noqa: PLC0415
    return m


def _ctx(**kwargs):
    """Build a minimal behave context mock with the given attributes."""
    ctx = MagicMock()
    for k, v in kwargs.items():
        setattr(ctx, k, v)
    return ctx


# ---------------------------------------------------------------------------
# ssh_return_code_is
# ---------------------------------------------------------------------------

class TestSshReturnCodeIs:
    def test_passes_when_codes_match(self):
        m = _import_dx_steps()
        ctx = _ctx(ssh_rc=0, command_stdout="ok", last_ssh_result=None)
        m.ssh_return_code_is(ctx, "0")  # should not raise

    def test_raises_when_codes_differ(self):
        m = _import_dx_steps()
        import pytest
        ctx = _ctx(ssh_rc=1, command_stdout="err", last_ssh_result=None)
        with pytest.raises(AssertionError, match="Expected SSH return code 0"):
            m.ssh_return_code_is(ctx, "0")

    def test_matches_nonzero_code(self):
        m = _import_dx_steps()
        ctx = _ctx(ssh_rc=42, command_stdout="", last_ssh_result=None)
        m.ssh_return_code_is(ctx, "42")  # should not raise

    def test_includes_stdout_in_error_message(self):
        m = _import_dx_steps()
        import pytest
        ctx = _ctx(ssh_rc=2, command_stdout="some output", last_ssh_result=None)
        with pytest.raises(AssertionError, match="some output"):
            m.ssh_return_code_is(ctx, "0")


# ---------------------------------------------------------------------------
# ssh_output_is
# ---------------------------------------------------------------------------

class TestSshOutputIs:
    def test_passes_on_exact_match(self):
        m = _import_dx_steps()
        ctx = _ctx(command_stdout="hello")
        m.ssh_output_is(ctx, "hello")  # should not raise

    def test_raises_on_mismatch(self):
        m = _import_dx_steps()
        import pytest
        ctx = _ctx(command_stdout="hello world")
        with pytest.raises(AssertionError, match="Expected"):
            m.ssh_output_is(ctx, "hello")

    def test_strips_whitespace_before_comparing(self):
        m = _import_dx_steps()
        ctx = _ctx(command_stdout="  hello  ")
        m.ssh_output_is(ctx, "hello")  # should not raise

    def test_raises_on_empty_vs_nonempty(self):
        m = _import_dx_steps()
        import pytest
        ctx = _ctx(command_stdout="data")
        with pytest.raises(AssertionError):
            m.ssh_output_is(ctx, "")

    def test_handles_missing_command_stdout(self):
        m = _import_dx_steps()
        import pytest
        ctx = MagicMock(spec=[])  # no attributes
        with pytest.raises(AssertionError):
            m.ssh_output_is(ctx, "expected")


# ---------------------------------------------------------------------------
# output_does_not_contain
# ---------------------------------------------------------------------------

class TestOutputDoesNotContain:
    def test_passes_when_text_absent(self):
        m = _import_dx_steps()
        ctx = _ctx(command_stdout="hello world")
        m.output_does_not_contain(ctx, "error")  # should not raise

    def test_raises_when_text_present(self):
        m = _import_dx_steps()
        import pytest
        ctx = _ctx(command_stdout="fatal error occurred")
        with pytest.raises(AssertionError, match="unexpectedly contains"):
            m.output_does_not_contain(ctx, "error")

    def test_passes_on_empty_output(self):
        m = _import_dx_steps()
        ctx = _ctx(command_stdout="")
        m.output_does_not_contain(ctx, "error")  # should not raise

    def test_handles_none_output(self):
        m = _import_dx_steps()
        ctx = _ctx(command_stdout=None)
        m.output_does_not_contain(ctx, "error")  # should not raise (None treated as "")


# ---------------------------------------------------------------------------
# output_contains
# ---------------------------------------------------------------------------

class TestOutputContains:
    def test_passes_when_text_present(self):
        m = _import_dx_steps()
        ctx = _ctx(command_stdout="hello world")
        m.output_contains(ctx, "world")  # should not raise

    def test_raises_when_text_absent(self):
        m = _import_dx_steps()
        import pytest
        ctx = _ctx(command_stdout="hello")
        with pytest.raises(AssertionError, match="does not contain"):
            m.output_contains(ctx, "world")

    def test_partial_match_passes(self):
        m = _import_dx_steps()
        ctx = _ctx(command_stdout="the quick brown fox")
        m.output_contains(ctx, "quick")  # should not raise

    def test_handles_none_output(self):
        m = _import_dx_steps()
        import pytest
        ctx = _ctx(command_stdout=None)
        with pytest.raises(AssertionError):
            m.output_contains(ctx, "something")


# ---------------------------------------------------------------------------
# _wait_until helper in developer suite
# ---------------------------------------------------------------------------

def _import_developer_steps():
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    qecore_stub = types.ModuleType("qecore")
    qecore_common_stub = types.ModuleType("qecore.common_steps")
    sys.modules["qecore"] = qecore_stub
    sys.modules["qecore.common_steps"] = qecore_common_stub

    ssh_steps_stub = types.ModuleType("tests.shared.ssh_steps")
    sys.modules["tests.shared"] = sys.modules.get("tests.shared", types.ModuleType("tests.shared"))
    sys.modules["tests.shared.ssh_steps"] = ssh_steps_stub

    for key in list(sys.modules):
        if "developer.features.steps.steps" in key:
            del sys.modules[key]

    import tests.developer.features.steps.steps as m  # noqa: PLC0415
    return m


class TestWaitUntil:
    def test_returns_immediately_when_predicate_true(self):
        m = _import_developer_steps()
        result = m._wait_until("should pass", lambda: 42, timeout=5)
        assert result == 42

    def test_raises_assertion_error_on_timeout(self):
        m = _import_developer_steps()
        import pytest
        with pytest.raises(AssertionError, match="timed out"):
            m._wait_until("timed out", lambda: False, timeout=0)

    def test_returns_truthy_value(self):
        m = _import_developer_steps()
        result = m._wait_until("ok", lambda: "hello", timeout=5)
        assert result == "hello"

    def test_ui_timeout_constant_is_positive(self):
        m = _import_developer_steps()
        assert m.UI_TIMEOUT_SECONDS > 0

"""Unit tests for tests/bazzite/features/steps/steps.py.

Bazzite steps use dogtail (AT-SPI) and Shell.Eval (subprocess gdbus calls).
All external dependencies are stubbed at import time — no GNOME session required.
"""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

def _import_bazzite_steps():
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    dogtail_stub = types.ModuleType("dogtail")
    tree_stub = types.ModuleType("dogtail.tree")
    tree_stub.root = MagicMock()
    predicate_stub = types.ModuleType("dogtail.predicate")
    predicate_stub.GenericPredicate = MagicMock
    sys.modules["dogtail"] = dogtail_stub
    sys.modules["dogtail.tree"] = tree_stub
    sys.modules["dogtail.predicate"] = predicate_stub

    qecore_stub = types.ModuleType("qecore")
    qecore_common_stub = types.ModuleType("qecore.common_steps")
    sys.modules["qecore"] = qecore_stub
    sys.modules["qecore.common_steps"] = qecore_common_stub

    for key in list(sys.modules):
        if "bazzite.features.steps.steps" in key:
            del sys.modules[key]

    import tests.bazzite.features.steps.steps as m  # noqa: PLC0415
    return m


def _ctx(**attrs):
    ctx = MagicMock()
    for k, v in attrs.items():
        setattr(ctx, k, v)
    return ctx


# ---------------------------------------------------------------------------
# _eval_bool helper
# ---------------------------------------------------------------------------

class TestEvalBool:
    def test_parses_true_from_gdbus_output(self):
        m = _import_bazzite_steps()
        gdbus_out = "(true, 'true')"
        with patch("tests.bazzite.features.steps.steps._shell_eval", return_value=gdbus_out):
            assert m._eval_bool("Main.overview.visible") is True

    def test_parses_false_from_gdbus_output(self):
        m = _import_bazzite_steps()
        gdbus_out = "(true, 'false')"
        with patch("tests.bazzite.features.steps.steps._shell_eval", return_value=gdbus_out):
            assert m._eval_bool("Main.overview.visible") is False

    def test_parses_double_quoted_true_gnome50(self):
        m = _import_bazzite_steps()
        gdbus_out = '(true, \'"true"\')'
        with patch("tests.bazzite.features.steps.steps._shell_eval", return_value=gdbus_out):
            assert m._eval_bool("js") is True

    def test_raises_on_unrecognized_output(self):
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._shell_eval", return_value="garbage"):
            with pytest.raises(AssertionError, match="Could not parse boolean"):
                m._eval_bool("js")


# ---------------------------------------------------------------------------
# _extension_state helper
# ---------------------------------------------------------------------------

class TestExtensionState:
    def _make_result(self, stdout, returncode=0):
        r = MagicMock()
        r.stdout = stdout
        r.returncode = returncode
        return r

    def test_parses_enabled_state_1(self):
        m = _import_bazzite_steps()
        out = "({'state': <uint32 1>, 'path': <'/usr/share/gnome-shell/extensions/uuid'>},)"
        with patch("subprocess.run", return_value=self._make_result(out)) as mock_run:
            assert m._extension_state(_ctx(), "some@uuid") == "1"
            # Verify UUID is wrapped in GVariant string quotes
            call_args = mock_run.call_args[0][0]
            assert "'some@uuid'" in call_args

    def test_parses_initialized_state_6(self):
        m = _import_bazzite_steps()
        out = "({'state': <uint32 6>, 'path': <'/usr/share/gnome-shell/extensions/uuid'>},)"
        with patch("subprocess.run", return_value=self._make_result(out)):
            assert m._extension_state(_ctx(), "some@uuid") == "6"

    def test_returns_99_when_gdbus_fails(self):
        m = _import_bazzite_steps()
        with patch("subprocess.run", return_value=self._make_result("", returncode=1)):
            assert m._extension_state(_ctx(), "missing@uuid") == "99"

    def test_returns_99_when_state_not_in_output(self):
        m = _import_bazzite_steps()
        with patch("subprocess.run", return_value=self._make_result("({})")):
            assert m._extension_state(_ctx(), "some@uuid") == "99"


# ---------------------------------------------------------------------------
# extension_is_enabled
# ---------------------------------------------------------------------------

class TestExtensionIsEnabled:
    def test_passes_when_state_is_1(self):
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._extension_state", return_value="1"):
            m.extension_is_enabled(_ctx(), "some@uuid")

    def test_raises_when_state_is_not_1(self):
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._extension_state", return_value="2"):
            with pytest.raises(AssertionError, match="not enabled"):
                m.extension_is_enabled(_ctx(), "some@uuid")

    def test_raises_when_uninstalled(self):
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._extension_state", return_value="99"):
            with pytest.raises(AssertionError, match="not enabled"):
                m.extension_is_enabled(_ctx(), "missing@uuid")

    def test_polls_past_initialized_state_6(self):
        """State 6 (INITIALIZED) is transient — step should poll until state=1."""
        m = _import_bazzite_steps()
        states = iter(["6", "6", "1"])
        with patch("tests.bazzite.features.steps.steps._extension_state", side_effect=states), \
             patch("tests.bazzite.features.steps.steps.time.sleep"):
            m.extension_is_enabled(_ctx(), "some@uuid")

    def test_polls_past_enabling_state_8(self):
        """State 8 (ENABLING) is transient — step should poll until state=1."""
        m = _import_bazzite_steps()
        states = iter(["8", "8", "1"])
        with patch("tests.bazzite.features.steps.steps._extension_state", side_effect=states), \
             patch("tests.bazzite.features.steps.steps.time.sleep"):
            m.extension_is_enabled(_ctx(), "some@uuid")

    def test_raises_after_timeout_in_state_6(self):
        """State 6 that never transitions should raise AssertionError after timeout."""
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._extension_state", return_value="6"), \
             patch("tests.bazzite.features.steps.steps.time.sleep"), \
             patch("tests.bazzite.features.steps.steps.time.monotonic",
                   side_effect=[0.0, 0.0, 91.0]):
            with pytest.raises(AssertionError, match="not enabled"):
                m.extension_is_enabled(_ctx(), "stuck@uuid")


# ---------------------------------------------------------------------------
# extension_is_installed
# ---------------------------------------------------------------------------

class TestExtensionIsInstalled:
    def test_passes_when_state_is_not_99(self):
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._extension_state", return_value="1"):
            m.extension_is_installed(_ctx(), "some@uuid")

    def test_raises_when_state_is_99(self):
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._extension_state", return_value="99"):
            with pytest.raises(AssertionError, match="not installed"):
                m.extension_is_installed(_ctx(), "missing@uuid")


# ---------------------------------------------------------------------------
# overview_is_open / overview_is_closed
# ---------------------------------------------------------------------------

class TestOverviewSteps:
    def test_overview_is_open_passes_when_visible(self):
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._eval_bool", return_value=True):
            m.overview_is_open(_ctx())

    def test_overview_is_open_raises_when_not_visible(self):
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._eval_bool", return_value=False):
            with pytest.raises(AssertionError, match="Overview is not open"):
                m.overview_is_open(_ctx())

    def test_overview_is_closed_passes_when_not_visible(self):
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._eval_bool", return_value=False):
            m.overview_is_closed(_ctx())

    def test_overview_is_closed_raises_when_visible(self):
        m = _import_bazzite_steps()
        with patch("tests.bazzite.features.steps.steps._eval_bool", return_value=True):
            with pytest.raises(AssertionError, match="Overview is still open"):
                m.overview_is_closed(_ctx())


# ---------------------------------------------------------------------------
# no_coredump_with_extensions
# ---------------------------------------------------------------------------

class TestNoCoredumpWithExtensions:
    def test_passes_when_no_coredumps(self):
        m = _import_bazzite_steps()
        mock_result = MagicMock()
        mock_result.stdout = "-- No entries --\n"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            m.no_coredump_with_extensions(_ctx())

    def test_raises_when_coredump_found(self):
        m = _import_bazzite_steps()
        mock_result = MagicMock()
        mock_result.stdout = "Jun 05 10:00:00 host gnome-shell[123]: signal=SIGABRT\n"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(AssertionError, match="coredumps found"):
                m.no_coredump_with_extensions(_ctx())

    def test_passes_when_coredumpctl_missing(self):
        m = _import_bazzite_steps()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            # Should not raise — gracefully skip when coredumpctl absent
            m.no_coredump_with_extensions(_ctx())

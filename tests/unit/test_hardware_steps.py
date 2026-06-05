"""Unit tests for tests/hardware/features/steps/steps.py."""
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

def _import_hardware_steps(run_ssh_side_effect=None):
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    ssh_steps_stub = types.ModuleType("tests.shared.ssh_steps")
    if run_ssh_side_effect is not None:
        ssh_steps_stub.run_ssh = run_ssh_side_effect
    else:
        ssh_steps_stub.run_ssh = MagicMock(return_value=("", 0))
    sys.modules["tests"] = sys.modules.get("tests", types.ModuleType("tests"))
    sys.modules["tests.shared"] = sys.modules.get("tests.shared", types.ModuleType("tests.shared"))
    sys.modules["tests.shared.ssh_steps"] = ssh_steps_stub

    for key in list(sys.modules):
        if "hardware.features.steps.steps" in key:
            del sys.modules[key]

    import tests.hardware.features.steps.steps as m  # noqa: PLC0415
    return m


def _ctx(**attrs):
    ctx = MagicMock()
    for k, v in attrs.items():
        setattr(ctx, k, v)
    return ctx


# ---------------------------------------------------------------------------
# audio_output_sink_is_detected
# ---------------------------------------------------------------------------

class TestAudioOutputSinkIsDetected:
    def test_passes_when_sink_found(self):
        calls = []

        def fake_run_ssh(context, cmd, timeout=60):
            calls.append(cmd)
            return ("alsa_output.pci-0000_00_1b.0.analog-stereo\tPipeWire\trunning", 0)

        m = _import_hardware_steps(run_ssh_side_effect=fake_run_ssh)
        ctx = _ctx()
        m.audio_output_sink_is_detected(ctx)
        assert calls

    def test_raises_when_no_sinks(self):
        def fake_run_ssh(context, cmd, timeout=60):
            return ("", 1)

        m = _import_hardware_steps(run_ssh_side_effect=fake_run_ssh)
        ctx = _ctx()
        with pytest.raises(AssertionError, match="No real audio sinks detected"):
            m.audio_output_sink_is_detected(ctx)

    def test_raises_when_rc_ok_but_empty_output(self):
        def fake_run_ssh(context, cmd, timeout=60):
            return ("", 0)

        m = _import_hardware_steps(run_ssh_side_effect=fake_run_ssh)
        ctx = _ctx()
        with pytest.raises(AssertionError, match="No real audio sinks detected"):
            m.audio_output_sink_is_detected(ctx)


# ---------------------------------------------------------------------------
# pipewire_reports_no_startup_errors
# ---------------------------------------------------------------------------

class TestPipewireReportsNoStartupErrors:
    def _make_run_ssh(self, active_return, journal_return):
        """Return a run_ssh stub that cycles through provided return values."""
        returns = [active_return, journal_return]
        call_idx = [0]

        def fake_run_ssh(context, cmd, timeout=60):
            idx = min(call_idx[0], len(returns) - 1)
            call_idx[0] += 1
            return returns[idx]

        return fake_run_ssh

    def test_passes_when_active_and_no_errors(self):
        fake = self._make_run_ssh(("active", 0), ("-- No entries --", 0))
        m = _import_hardware_steps(run_ssh_side_effect=fake)
        ctx = _ctx()
        m.pipewire_reports_no_startup_errors(ctx)

    def test_raises_when_pipewire_not_active(self):
        fake = self._make_run_ssh(("inactive", 1), ("", 0))
        m = _import_hardware_steps(run_ssh_side_effect=fake)
        ctx = _ctx()
        with pytest.raises(AssertionError, match="pipewire.service is not active"):
            m.pipewire_reports_no_startup_errors(ctx)

    def test_raises_when_journal_has_pipewire_errors(self):
        journal_out = "Jun 05 10:00:00 host pipewire[123]: ERROR: failed to init"
        fake = self._make_run_ssh(("active", 0), (journal_out, 0))
        m = _import_hardware_steps(run_ssh_side_effect=fake)
        ctx = _ctx()
        with pytest.raises(AssertionError, match="PipeWire startup errors found"):
            m.pipewire_reports_no_startup_errors(ctx)

    def test_passes_when_journal_has_no_pipewire_entries(self):
        journal_out = "Jun 05 10:00:00 host kernel: some other message"
        fake = self._make_run_ssh(("active", 0), (journal_out, 0))
        m = _import_hardware_steps(run_ssh_side_effect=fake)
        ctx = _ctx()
        m.pipewire_reports_no_startup_errors(ctx)

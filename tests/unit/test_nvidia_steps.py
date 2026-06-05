"""Unit tests for tests/nvidia/features/steps/steps.py."""
import sys
import types
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

def _import_nvidia_steps():
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    ssh_steps_stub = types.ModuleType("tests.shared.ssh_steps")
    ssh_steps_stub.run_ssh = MagicMock(return_value=("", 0))
    sys.modules["tests"] = sys.modules.get("tests", types.ModuleType("tests"))
    sys.modules["tests.shared"] = sys.modules.get("tests.shared", types.ModuleType("tests.shared"))
    sys.modules["tests.shared.ssh_steps"] = ssh_steps_stub

    for key in list(sys.modules):
        if "nvidia.features.steps.steps" in key:
            del sys.modules[key]

    import tests.nvidia.features.steps.steps as m  # noqa: PLC0415
    return m


def _ctx(**attrs):
    ctx = MagicMock()
    for k, v in attrs.items():
        setattr(ctx, k, v)
    return ctx


# ---------------------------------------------------------------------------
# nvidia_vm_reachable
# ---------------------------------------------------------------------------

class TestNvidiaVmReachable:
    def test_skips_scenario_with_gpu_passthrough_message(self):
        m = _import_nvidia_steps()
        ctx = _ctx()
        ctx.scenario = MagicMock()
        m.nvidia_vm_reachable(ctx)
        ctx.scenario.skip.assert_called_once()
        skip_msg = ctx.scenario.skip.call_args[0][0]
        assert "GPU passthrough" in skip_msg or "passthrough" in skip_msg.lower()

    def test_does_not_raise(self):
        m = _import_nvidia_steps()
        ctx = _ctx()
        ctx.scenario = MagicMock()
        # Should not raise any exception
        m.nvidia_vm_reachable(ctx)

"""Unit tests for the installer suite's LUKS gating (projectbluefin/dakota#651).

The `@luks` scenario asserts the projectbluefin/common#385 `rd.luks.name=`
parsing fix against a real installed system. It used to be gated solely on a
`LUKS_ENABLED` environment variable that nothing in the repo ever set — the
reusable `e2e.yml` passes a fixed env list to the installer suite with no LUKS
entry — so the scenario skipped on every run and the assertion was never
exercised. These tests pin the runtime probe that replaced that dead gate.
"""

from __future__ import annotations

import importlib
import subprocess

import pytest


ENVIRONMENT_MODULE = "tests.installer.features.environment"


@pytest.fixture
def env_module(monkeypatch):
    """Import the installer environment with LUKS_ENABLED unset by default."""
    monkeypatch.delenv("LUKS_ENABLED", raising=False)
    module = importlib.import_module(ENVIRONMENT_MODULE)
    return importlib.reload(module)


class _FakeScenario:
    def __init__(self, tags=None):
        self.tags = list(tags or [])
        self.effective_tags = self.tags
        self.skip_message: str | None = None
        self.skipped = False

    def skip(self, message: str | None = None) -> None:
        self.skipped = True
        self.skip_message = message


class _Context:
    """Minimal behave context stand-in."""

    def __init__(self, **kwargs):
        self.luks_enabled = None
        self.ssh_key = "/tmp/key"
        self.vm_ip = "192.0.2.10"
        self.ssh_user = "bluefin-test"
        self.ssh_port = None
        for key, value in kwargs.items():
            setattr(self, key, value)


def _patch_probe(monkeypatch, env_module, result):
    """Patch run_ssh as the installer environment resolves it."""
    calls: list[str] = []

    def fake_run_ssh(context, cmd, timeout=60):
        calls.append(cmd)
        if isinstance(result, BaseException):
            raise result
        return "", result

    import tests.shared.ssh_steps as ssh_steps

    # Other unit tests replace this module with minimal stubs while importing
    # suite step modules. Under xdist, an installer test can inherit such a
    # stub, so do not require the production attribute to already exist.
    monkeypatch.setattr(ssh_steps, "run_ssh", fake_run_ssh, raising=False)
    return calls


# ── the override still works in both directions ───────────────────────────────


class TestLuksOverride:
    @pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", " yes "])
    def test_truthy_values_force_the_scenario_on(self, monkeypatch, env_module, value):
        monkeypatch.setenv("LUKS_ENABLED", value)
        assert env_module._luks_override() is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "anything-else"])
    def test_other_values_force_the_scenario_off(self, monkeypatch, env_module, value):
        monkeypatch.setenv("LUKS_ENABLED", value)
        assert env_module._luks_override() is False

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_unset_or_blank_means_undecided_not_false(self, monkeypatch, env_module, value):
        """The distinction that fixes #651: unset must mean "probe", not "no LUKS"."""
        if value is None:
            monkeypatch.delenv("LUKS_ENABLED", raising=False)
        else:
            monkeypatch.setenv("LUKS_ENABLED", value)
        assert env_module._luks_override() is None

    def test_override_wins_without_probing(self, monkeypatch, env_module):
        monkeypatch.setenv("LUKS_ENABLED", "true")
        calls = _patch_probe(monkeypatch, env_module, 1)  # probe would say "no LUKS"

        assert env_module.target_uses_luks(_Context()) is True
        assert calls == []


# ── the probe itself ──────────────────────────────────────────────────────────


class TestTargetUsesLuks:
    def test_true_when_the_target_has_a_crypt_device(self, monkeypatch, env_module):
        _patch_probe(monkeypatch, env_module, 0)
        assert env_module.target_uses_luks(_Context()) is True

    def test_false_when_the_target_has_no_crypt_device(self, monkeypatch, env_module):
        _patch_probe(monkeypatch, env_module, 1)
        assert env_module.target_uses_luks(_Context()) is False

    def test_false_when_the_dut_is_unreachable(self, monkeypatch, env_module):
        _patch_probe(monkeypatch, env_module, OSError("no route to host"))
        assert env_module.target_uses_luks(_Context()) is False

    def test_false_when_the_probe_times_out(self, monkeypatch, env_module):
        _patch_probe(monkeypatch, env_module, subprocess.TimeoutExpired("ssh", 30))
        assert env_module.target_uses_luks(_Context()) is False

    def test_probe_inspects_block_device_types(self, monkeypatch, env_module):
        calls = _patch_probe(monkeypatch, env_module, 0)
        env_module.target_uses_luks(_Context())

        assert calls == ["lsblk -rno TYPE | grep -qx crypt"]

    def test_probe_result_is_cached_on_the_context(self, monkeypatch, env_module):
        calls = _patch_probe(monkeypatch, env_module, 0)
        context = _Context()
        env_module.target_uses_luks(context)
        env_module.target_uses_luks(context)

        assert context.luks_enabled is True
        assert len(calls) == 1, "the probe must not re-run per scenario"


# ── before_scenario gating ────────────────────────────────────────────────────


class TestBeforeScenarioLuksGate:
    def test_luks_scenario_runs_on_a_luks_target(self, monkeypatch, env_module):
        _patch_probe(monkeypatch, env_module, 0)
        scenario = _FakeScenario(["installer", "luks"])

        env_module.before_scenario(_Context(), scenario)

        assert not scenario.skipped

    def test_luks_scenario_skips_on_a_plain_target(self, monkeypatch, env_module):
        _patch_probe(monkeypatch, env_module, 1)
        scenario = _FakeScenario(["installer", "luks"])

        env_module.before_scenario(_Context(), scenario)

        assert scenario.skipped
        assert "LUKS" in scenario.skip_message

    def test_non_luks_scenarios_are_never_probed(self, monkeypatch, env_module):
        calls = _patch_probe(monkeypatch, env_module, 1)
        scenario = _FakeScenario(["installer", "uefi"])

        env_module.before_scenario(_Context(), scenario)

        assert not scenario.skipped
        assert calls == []


# ── the gate must not silently become unreachable again ───────────────────────


def test_luks_gate_does_not_depend_on_an_unset_env_var_alone(env_module):
    """Regression guard for the #651 defect.

    Before this fix, `before_all` collapsed an unset `LUKS_ENABLED` to False and
    `before_scenario` skipped on it, so the `@luks` scenario could never run —
    a green report that asserted nothing. If someone reintroduces a pure env-var
    gate, `target_uses_luks` disappears and this fails.
    """
    assert hasattr(env_module, "target_uses_luks")
    assert callable(env_module.target_uses_luks)

    source = importlib.import_module(ENVIRONMENT_MODULE).__file__
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    assert "target_uses_luks(context)" in text, (
        "before_scenario must gate @luks on the runtime probe, not on the env var"
    )

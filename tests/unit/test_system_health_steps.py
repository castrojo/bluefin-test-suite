"""Unit tests for tests/smoke/features/steps/system_health_steps.py.

Tests the pure helper functions: _has_image_reference, _running_in_vm,
and IGNORED_FAILED_UNITS_IN_VM set membership.  No live systemd or
subprocess calls.
"""

from unittest.mock import patch

from tests.smoke.features.steps import system_health_steps


# ---------------------------------------------------------------------------
# _has_image_reference — recursive dict/list search
# ---------------------------------------------------------------------------

class TestHasImageReference:
    def test_detects_imageDigest_key(self):
        data = {"imageDigest": "sha256:abc123"}
        assert system_health_steps._has_image_reference(data) is True

    def test_detects_image_key(self):
        data = {"image": "ghcr.io/projectbluefin/bluefin:latest"}
        assert system_health_steps._has_image_reference(data) is True

    def test_detects_container_type_key(self):
        data = {"status": {"type": "container"}}
        assert system_health_steps._has_image_reference(data) is True

    def test_returns_false_for_empty_dict(self):
        assert system_health_steps._has_image_reference({}) is False

    def test_returns_false_for_unrelated_keys(self):
        data = {"status": "ok", "version": "1.0"}
        assert system_health_steps._has_image_reference(data) is False

    def test_finds_nested_imageDigest(self):
        data = {"status": {"booted": {"imageDigest": "sha256:abc"}}}
        assert system_health_steps._has_image_reference(data) is True

    def test_finds_image_ref_inside_list(self):
        data = [{"other": 1}, {"imageDigest": "sha256:abc"}]
        assert system_health_steps._has_image_reference(data) is True

    def test_returns_false_for_empty_list(self):
        assert system_health_steps._has_image_reference([]) is False

    def test_returns_false_for_list_of_unrelated_dicts(self):
        data = [{"foo": "bar"}, {"baz": 42}]
        assert system_health_steps._has_image_reference(data) is False

    def test_handles_deeply_nested_structure(self):
        data = {"a": {"b": {"c": [{"d": {"image": "ref"}}]}}}
        assert system_health_steps._has_image_reference(data) is True

    def test_returns_false_for_scalar_string(self):
        assert system_health_steps._has_image_reference("just a string") is False

    def test_returns_false_for_none(self):
        assert system_health_steps._has_image_reference(None) is False

    def test_returns_false_for_integer(self):
        assert system_health_steps._has_image_reference(42) is False


# ---------------------------------------------------------------------------
# _running_in_vm
# ---------------------------------------------------------------------------

class TestRunningInVm:
    def test_returns_true_when_detect_virt_succeeds(self):
        with patch.object(system_health_steps, "_run_host", return_value=("kvm", 0, "")):
            assert system_health_steps._running_in_vm() is True

    def test_returns_false_when_detect_virt_fails(self):
        with patch.object(system_health_steps, "_run_host", return_value=("", 1, "")):
            assert system_health_steps._running_in_vm() is False


class TestAtSpiBus:
    def test_queries_the_vm_session_bus(self):
        with patch.object(
            system_health_steps,
            "_run_host",
            return_value=("('unix:path=/run/user/1000/at-spi/bus_0',)", 0, ""),
        ) as run_host:
            system_health_steps.at_spi_accessibility_bus_is_reachable_from_the_gnome_session(None)

        command = run_host.call_args.args[0]
        assert "source /tmp/session.env" in command
        assert "org.a11y.Bus.GetAddress" in command

    def test_rejects_an_empty_bus_address(self):
        import pytest

        with patch.object(system_health_steps, "_run_host", return_value=("('',)", 0, "")), \
             pytest.raises(AssertionError, match="no Unix address"):
            system_health_steps.at_spi_accessibility_bus_is_reachable_from_the_gnome_session(None)


# ---------------------------------------------------------------------------
# IGNORED_FAILED_UNITS_IN_VM — set membership
# ---------------------------------------------------------------------------

class TestIgnoredFailedUnits:
    def test_known_units_are_in_set(self):
        expected = {
            "mcelog.service",
            "avahi-daemon.service",
            "cups.service",
            "bootloader-update.service",
            "input-remapper.service",
            "nvidia-persistenced.service",
            "fwupd-refresh.service",
            "auditd.service",
            "systemd-resolved.service",
        }
        for unit in expected:
            assert unit in system_health_steps.IGNORED_FAILED_UNITS_IN_VM, (
                f"{unit} should be in IGNORED_FAILED_UNITS_IN_VM"
            )

    def test_unknown_units_are_not_in_set(self):
        unknown = {"sshd.service", "gdm.service", "NetworkManager.service"}
        for unit in unknown:
            assert unit not in system_health_steps.IGNORED_FAILED_UNITS_IN_VM, (
                f"{unit} should NOT be in IGNORED_FAILED_UNITS_IN_VM"
            )

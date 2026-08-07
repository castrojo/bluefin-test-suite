"""Regression checks for shared E2E workflow setup."""

from pathlib import Path


def test_e2e_preserves_image_enabled_extensions():
    workflow = (
        Path(__file__).parents[2] / ".github" / "workflows" / "e2e.yml"
    ).read_text()
    local_override = workflow.partition(
        'sudo mkdir -p "${DEP}/etc/dconf/db/local.d"'
    )[2].partition("sudo chroot")[0]

    assert "allow-extension-installation=true" in local_override
    assert "enabled-extensions" not in local_override
    assert "gnome-extensions enable unsafe-mode@bluefin-test" in workflow


def test_e2e_keeps_tailscale_running_with_sufficient_storage():
    workflow = (
        Path(__file__).parents[2] / ".github" / "workflows" / "e2e.yml"
    ).read_text()

    assert "fallocate -l 32G disk.raw" in workflow
    assert "systemd.mask=tailscaled.service" not in workflow


def test_e2e_filters_all_non_runnable_scenario_tags():
    workflow = (
        Path(__file__).parents[2] / ".github" / "workflows" / "e2e.yml"
    ).read_text()

    assert (
        'BEHAVE_TAG_ARGS="--tags ~quarantine --tags ~pending --tags ~future"'
        in workflow
    )

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

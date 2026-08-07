"""Contract tests for scripts/install-kde-webdriver.sh."""

from __future__ import annotations

import re
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "install-kde-webdriver.sh"
)


def _script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_script_pins_full_commit_sha():
    text = _script_text()
    match = re.search(
        r'readonly SELENIUM_AT_SPI_SHA="([0-9a-f]{40})"',
        text,
    )
    assert match is not None


def test_script_documents_loopback_only_security_contract():
    text = _script_text()
    assert "It MUST bind 127.0.0.1 (loopback) only" in text
    assert "Do NOT set HOST=0.0.0.0" in text
    assert "Environment=FLASK_PORT=${FLASK_PORT:-4723}" in text
    assert "Environment=HOST=" not in text


def test_script_skip_paths_emit_reason_and_exit_zero():
    text = _script_text()
    skip_branches = re.findall(r"KDE_WEBDRIVER_SKIP=.*\n\s*exit 0", text)
    assert len(skip_branches) >= 3
    assert "supported 5.27 LTS baseline" in text
    assert "unsupported distro" in text

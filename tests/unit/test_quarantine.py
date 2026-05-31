"""Unit tests for tests/shared/quarantine.py."""

from __future__ import annotations

import pytest

from tests.shared.quarantine import skip_quarantine


# ── helpers ───────────────────────────────────────────────────────────────────


class _FakeScenario:
    """Minimal behave Scenario stand-in for unit testing."""

    def __init__(self, tags=None, *, skip_raises=False):
        self.tags = list(tags or [])
        self.effective_tags = self.tags
        self.skip_raises = skip_raises
        self.skip_message: str | None = None
        self.skipped = False

    def skip(self, message: str | None = None) -> None:
        if self.skip_raises and message is not None:
            raise TypeError("skip() takes no arguments")
        self.skipped = True
        self.skip_message = message


# ── tests ─────────────────────────────────────────────────────────────────────


def test_non_quarantined_scenario_is_not_skipped():
    """Scenarios without @quarantine tag return False and are not skipped."""
    scenario = _FakeScenario(tags=["smoke", "top_bar"])
    result = skip_quarantine(scenario)
    assert result is False
    assert not scenario.skipped


def test_quarantined_scenario_is_skipped_with_message():
    """@quarantine scenario is skipped with the standard reason string."""
    scenario = _FakeScenario(tags=["quarantine", "brew"])
    result = skip_quarantine(scenario)
    assert result is True
    assert scenario.skipped
    assert scenario.skip_message is not None
    assert "quarantine" in scenario.skip_message.lower()


def test_quarantine_tag_in_effective_tags_via_attribute():
    """Uses effective_tags when the attribute exists."""
    scenario = _FakeScenario(tags=[])
    scenario.effective_tags = ["quarantine", "extra"]
    result = skip_quarantine(scenario)
    assert result is True
    assert scenario.skipped


def test_quarantine_falls_back_to_no_arg_skip_on_type_error():
    """Falls back to scenario.skip() (no args) when skip(msg) raises TypeError.

    Older behave versions do not accept a message argument.
    """
    scenario = _FakeScenario(tags=["quarantine"], skip_raises=True)
    # Should not raise even though skip(msg) would raise TypeError.
    result = skip_quarantine(scenario)
    assert result is True
    assert scenario.skipped
    # No message stored because the no-arg path was taken.
    assert scenario.skip_message is None


def test_empty_tags_are_not_quarantined():
    """Scenario with no tags at all is not quarantined."""
    scenario = _FakeScenario(tags=[])
    assert skip_quarantine(scenario) is False
    assert not scenario.skipped


def test_quarantine_tag_mixed_with_others():
    """@quarantine alongside other tags still triggers skip."""
    scenario = _FakeScenario(tags=["smoke", "quarantine", "sla_10s"])
    result = skip_quarantine(scenario)
    assert result is True
    assert scenario.skipped

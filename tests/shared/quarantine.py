"""Shared helpers for @quarantine, @pending and @future scenario handling."""

from __future__ import annotations


_SKIP_REASONS = {
    "quarantine": "@quarantine — known flaky, skipping",
    "pending": "@pending — placeholder coverage, skipping",
    "future": "@future — planned coverage not yet runnable, skipping",
}

# Order matters only for the reported reason when several tags coexist.
# Must match the precedence documented in
# docs/skills/test-authoring/suite-map/SKILL.md.
_SKIP_TAGS = ("quarantine", "future", "pending")


def skip_quarantine(scenario) -> bool:
    scenario_tags = set(getattr(scenario, "effective_tags", scenario.tags))
    for tag in _SKIP_TAGS:
        if tag not in scenario_tags:
            continue
        try:
            scenario.skip(_SKIP_REASONS[tag])
        except TypeError:
            scenario.skip()
        return True
    return False

"""Shared helpers for @quarantine and @pending scenario handling."""

from __future__ import annotations


_SKIP_REASONS = {
    "quarantine": "@quarantine — known flaky, skipping",
    "pending": "@pending — placeholder coverage, skipping",
}


def skip_quarantine(scenario) -> bool:
    scenario_tags = set(getattr(scenario, "effective_tags", scenario.tags))
    for tag in ("quarantine", "pending"):
        if tag not in scenario_tags:
            continue
        try:
            scenario.skip(_SKIP_REASONS[tag])
        except TypeError:
            scenario.skip()
        return True
    return False

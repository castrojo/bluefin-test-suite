"""Shared helpers for @quarantine scenario handling."""

from __future__ import annotations


def skip_quarantine(scenario) -> bool:
    scenario_tags = set(getattr(scenario, "effective_tags", scenario.tags))
    if "quarantine" not in scenario_tags:
        return False
    try:
        scenario.skip("@quarantine — known flaky, skipping")
    except TypeError:
        scenario.skip()
    return True

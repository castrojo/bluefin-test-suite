"""AT-SPI diagnostics shared by GUI suites.

Diagnostics only: every helper here reports what the accessibility bus
currently exposes and never raises, so a caller can enrich a failure message
without changing whether the assertion failed.
"""

from __future__ import annotations


def accessible_application_names() -> list[str]:
    """Names of every application currently registered on the AT-SPI bus.

    Returns a single ``<AT-SPI unavailable: ...>`` entry instead of raising
    when dogtail or the accessibility bus is not reachable — callers use this
    to explain a launch failure, so it must not introduce a second one.
    """
    try:
        from dogtail.tree import root

        return sorted({app.name or "<unnamed>" for app in root.applications()})
    except Exception as error:  # noqa: BLE001 - diagnostics must never raise
        return [f"<AT-SPI unavailable: {error}>"]

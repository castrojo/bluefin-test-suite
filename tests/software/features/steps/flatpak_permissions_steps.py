"""Flatpak per-app permission management steps for the software suite.

Flatseal is a GUI front end over ``flatpak override`` and the portal permission
store.  The steps here assert the same state Flatseal manipulates using only the
flatpak CLI, so they run without a desktop session and without depending on which
Flatpaks happen to be installed on the image under test.
"""
from __future__ import annotations

from behave import step

try:  # behave loads the suite steps directory as a top-level ``steps`` package
    from steps.steps import _flatpak
except ImportError:  # pytest / direct module import
    from tests.software.features.steps.steps import _flatpak


# Synthetic application ID used by every override round-trip in
# flatpak_permissions_mgmt.feature. It is never installed, so setting and
# resetting overrides on it cannot clobber real user state.
PROBE_APP_ID = "org.projectbluefin.TestsuitePermissionProbe"


def reset_probe_overrides(context) -> None:
    """Drop any override the permission-management scenarios installed.

    Called from ``after_scenario`` so a scenario that fails before its trailing
    reset step cannot leave the synthetic override installed and contaminate
    retries or later scenarios.
    """
    return _flatpak(context, ["override", "--user", "--reset", PROBE_APP_ID], timeout=30)


def parse_flatpak_context(text: str) -> dict[str, dict[str, str]]:
    """Parse the keyfile emitted by ``flatpak override --show``.

    Returns ``{section: {key: raw_value}}``.  Blank lines, comments and stray
    values outside any section are ignored.
    """
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            sections.setdefault(current, {})
            continue
        if current is None or "=" not in line:
            continue
        key, _, value = line.partition("=")
        sections[current][key.strip()] = value.strip()
    return sections


def context_values(text: str, key: str, section: str = "Context") -> list[str]:
    """Return the semicolon-separated values recorded for ``section``/``key``."""
    raw = parse_flatpak_context(text).get(section, {}).get(key, "")
    return [item for item in (part.strip() for part in raw.split(";")) if item]


def override_keys(text: str) -> set[str]:
    """Return ``"Section.key"`` names for every permission entry present."""
    return {
        f"{section}.{key}"
        for section, entries in parse_flatpak_context(text).items()
        for key in entries
    }


def _user_override_output(context, app_id: str) -> str:
    result = _flatpak(context, ["override", "--user", "--show", app_id])
    assert result.returncode == 0, (
        f"flatpak override --user --show {app_id} failed: rc={result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    return result.stdout


@step('Flatpak user override for "{app_id}" grants "{key}" value "{value}"')
def flatpak_user_override_grants(context, app_id: str, key: str, value: str) -> None:
    output = _user_override_output(context, app_id)
    values = context_values(output, key)
    assert value in values, (
        f"Expected [Context] {key} to include {value!r} for {app_id}, got {values}\n{output}"
    )


@step('Flatpak user override for "{app_id}" section "{section}" sets "{key}" to "{value}"')
def flatpak_user_override_section_sets(
    context, app_id: str, section: str, key: str, value: str
) -> None:
    output = _user_override_output(context, app_id)
    entries = parse_flatpak_context(output).get(section, {})
    assert entries.get(key) == value, (
        f"Expected [{section}] {key}={value} for {app_id}, "
        f"got {entries.get(key)!r}\n{output}"
    )


@step('Flatpak user override for "{app_id}" records at least "{count}" permission keys')
def flatpak_user_override_records_at_least(context, app_id: str, count: str) -> None:
    output = _user_override_output(context, app_id)
    keys = override_keys(output)
    assert len(keys) >= int(count), (
        f"Expected at least {count} permission keys for {app_id}, got {sorted(keys)}\n{output}"
    )


@step('Flatpak user override for "{app_id}" records no permission keys')
def flatpak_user_override_records_none(context, app_id: str) -> None:
    output = _user_override_output(context, app_id)
    keys = override_keys(output)
    assert not keys, (
        f"Expected no permission keys for {app_id} after reset, got {sorted(keys)}\n{output}"
    )


@step("Every installed flatpak app exposes a parsable permission set")
def every_installed_app_exposes_permissions(context) -> None:
    """Sweep the install set; passes trivially when nothing is installed.

    CI masks ``flatpak-preinstall.service`` and does not seed ``/var/lib/flatpak``,
    so an empty install set is an expected, valid outcome here.
    """
    listing = _flatpak(context, ["list", "--app", "--columns=application"], timeout=30)
    assert listing.returncode == 0, (
        f"flatpak list failed: rc={listing.returncode}\n"
        f"stdout={listing.stdout}\nstderr={listing.stderr}"
    )
    app_ids = [line.strip() for line in listing.stdout.splitlines() if line.strip()]
    failures: list[str] = []
    for app_id in app_ids:
        result = _flatpak(context, ["info", "--show-permissions", app_id], timeout=30)
        if result.returncode != 0:
            failures.append(f"{app_id}: rc={result.returncode} stderr={result.stderr.strip()}")
            continue
        if "Context" not in parse_flatpak_context(result.stdout):
            failures.append(f"{app_id}: no [Context] section in:\n{result.stdout}")
    assert not failures, "Unparsable permission sets:\n" + "\n".join(failures)
    context.flatpak_apps_checked = len(app_ids)


@step("Flatpak portal permission store is queryable")
def flatpak_portal_permission_store_is_queryable(context) -> None:
    result = _flatpak(context, ["permissions"], timeout=30)
    assert result.returncode == 0, (
        f"flatpak permissions failed: rc={result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )

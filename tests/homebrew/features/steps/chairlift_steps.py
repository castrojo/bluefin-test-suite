"""ChairLift step definitions for the homebrew suite.

Covers Bluefin's packaging of the ChairLift managed cask: the brew-preinstall
service and managed-state contract, the user-scoped desktop/icon
integration installed by the Homebrew cask, the maintainer `config.yml`
surfaced through ChairLift's own UI, and the authenticated, download-only
bootc staging helper.

Upstream ChairLift already unit-tests config parsing, Homebrew search/trust/
bundle behaviour, PolicyKit action shape, and bootc progress streaming (see
frostyard/chairlift's own test suite). This module intentionally covers only
what is specific to how Bluefin ships and configures ChairLift: the cask
lifecycle, the installed desktop/icon files, the rendered UI for Bluefin's
`config.yml`, and the fixed paths the bootc PolicyKit action depends on.
"""
import json
import os
import re
import shlex
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from behave import step
from qecore.common_steps import *  # noqa: F401,F403

from tests.shared.a11y import accessible_application_names


HOMEBREW_PREFIX = "/var/home/linuxbrew/.linuxbrew"
BREW = f"{HOMEBREW_PREFIX}/bin/brew"
CHAIRLIFT_BIN = Path(f"{HOMEBREW_PREFIX}/bin/chairlift")
CHAIRLIFT_WRAPPER = f"{HOMEBREW_PREFIX}/bin/chairlift-wrapper"
STATE = Path.home() / ".local/share/ublue-os/brew-preinstall-state.json"
DESKTOP_FILE = Path.home() / ".local/share/applications/org.frostyard.ChairLift.desktop"
ICON_DIR = Path.home() / ".local/share/icons/hicolor"
SCALABLE_ICON = ICON_DIR / "scalable/apps/org.frostyard.ChairLift.svg"
SCALABLE_FLOWER_ICON = ICON_DIR / "scalable/apps/org.frostyard.ChairLift-flower.svg"
SYMBOLIC_ICON = ICON_DIR / "symbolic/apps/org.frostyard.ChairLift-symbolic.svg"
POLICY_FILE = Path("/usr/share/polkit-1/actions/org.frostyard.ChairLift.bootc.policy")
BOOTC_HELPER = Path("/usr/libexec/bootc-update-stage")
BOOTC_ACTION_ID = "org.frostyard.ChairLift.bootc.stage"
EXEC_RE = re.compile(r"^\s*exec\b(.*)$", re.MULTILINE)

#: AT-SPI application root — the binary name from g_get_prgname(), registered
#: in environment.py. "ChairLift" is only the frame title.
A11Y_ROOT_NAME = "chairlift"


#: The unit is Type=oneshot with RemainAfterExit=true, so a clean completed run
#: is loaded/active/exited/success. Asserting only Result=success would also
#: pass for a unit that never ran (Result defaults to "success" while
#: ActiveState is "inactive"), which is the regression this lane must catch.
PREINSTALL_STATE = {
    "LoadState": "loaded",
    "ActiveState": "active",
    "SubState": "exited",
    "Result": "success",
}


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def _parse_properties(output: str) -> dict[str, str]:
    """Parse `systemctl show` key=value output into a dict."""
    properties: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key.strip()] = value.strip()
    return properties


def _chairlift_root(context):
    """ChairLift's AT-SPI root, or an AssertionError naming what *is* registered.

    A missing root means the app never launched, exited immediately, or the
    a11y bus is unreachable — all of which otherwise surface as the same
    opaque dogtail SearchError. The failure is re-raised, never downgraded:
    the diagnostics only say which application names the bus does expose.
    """
    try:
        return context.chairlift.instance
    except Exception as error:  # noqa: BLE001 - re-raised as an assertion below
        raise AssertionError(
            f"ChairLift is not on the AT-SPI bus under application root "
            f"{A11Y_ROOT_NAME!r} ({type(error).__name__}: {error}). "
            f"Registered AT-SPI applications: {accessible_application_names()}. "
            f"The root is the binary name (g_get_prgname()), not the frame "
            f"title 'ChairLift'; an empty or unavailable list means the app "
            f"never launched or accessibility is off, not a UI regression."
        ) from error


def _showing_named(context, name: str) -> list:
    """Visible AT-SPI nodes in ChairLift whose accessible name equals `name`."""
    return _chairlift_root(context).findChildren(
        lambda node: node.name == name and node.showing
    )


@step("The brew-preinstall user service completed successfully")
def brew_preinstall_completed(context) -> None:
    result = _run(
        "systemctl", "--user", "show", "brew-preinstall.service",
        *(f"--property={name}" for name in PREINSTALL_STATE),
    )
    assert result.returncode == 0, (
        f"systemctl --user show brew-preinstall.service failed "
        f"(rc={result.returncode}): {result.stderr.strip()}"
    )
    properties = _parse_properties(result.stdout)
    actual = {name: properties.get(name) for name in PREINSTALL_STATE}
    assert actual == PREINSTALL_STATE, (
        f"brew-preinstall.service did not complete successfully: "
        f"expected {PREINSTALL_STATE}, got {actual}"
    )


@step('The managed Homebrew state lists cask "{name}"')
def managed_state_lists_cask(context, name: str) -> None:
    data = json.loads(STATE.read_text(encoding="utf-8"))
    assert name in data["casks"], data


@step('Homebrew reports cask "{name}" installed')
def brew_reports_cask(context, name: str) -> None:
    result = _run(BREW, "list", "--cask", name)
    assert result.returncode == 0, result.stdout + result.stderr


@step("The ChairLift command is available")
def chairlift_command_available(context) -> None:
    assert CHAIRLIFT_BIN.is_file(), f"Missing ChairLift binary at {CHAIRLIFT_BIN}"
    assert os.access(CHAIRLIFT_BIN, os.X_OK), f"{CHAIRLIFT_BIN} is not executable"


@step("The ChairLift desktop entry launches the Homebrew wrapper")
def chairlift_desktop_entry_launches_wrapper(context) -> None:
    content = DESKTOP_FILE.read_text(encoding="utf-8")
    match = re.search(r"^Exec=(.*)$", content, re.MULTILINE)
    assert match, f"No Exec= line found in {DESKTOP_FILE}:\n{content}"
    argv = shlex.split(match.group(1).strip())
    assert len(argv) == 1, (
        f"Expected Exec={CHAIRLIFT_WRAPPER} with no extra arguments, "
        f"got Exec={match.group(1).strip()}"
    )
    # /home is a symlink to /var/home on bootc images, so the cask's spelling
    # of the wrapper path may differ from ours character-for-character while
    # naming the same file. realpath both sides to keep the comparison exact
    # without being fooled by the symlink spelling.
    actual = Path(argv[0]).resolve()
    expected = Path(CHAIRLIFT_WRAPPER).resolve()
    assert actual == expected, (
        f"Expected Exec to resolve to {expected}, got {argv[0]} "
        f"(resolves to {actual})"
    )


@step("The ChairLift scalable and symbolic icons exist")
def chairlift_icons_exist(context) -> None:
    for icon in (SCALABLE_ICON, SCALABLE_FLOWER_ICON, SYMBOLIC_ICON):
        assert icon.is_file() and icon.stat().st_size > 0, f"Missing or empty icon: {icon}"


@step("ChairLift has no configuration error toast")
def chairlift_has_no_configuration_error_toast(context) -> None:
    matches = _chairlift_root(context).findChildren(
        lambda node: node.showing and "Configuration error" in (node.name or "")
    )
    assert not matches, f"Unexpected configuration error toast: {[m.name for m in matches]}"


@step('ChairLift shows page "{name}"')
def chairlift_shows_page(context, name: str) -> None:
    assert _showing_named(context, name), f"ChairLift page not visible: {name}"


@step('ChairLift hides page "{name}"')
def chairlift_hides_page(context, name: str) -> None:
    matches = _showing_named(context, name)
    assert not matches, f"ChairLift page unexpectedly visible: {name}"


@step('ChairLift shows group "{name}"')
def chairlift_shows_group(context, name: str) -> None:
    assert _showing_named(context, name), f"ChairLift group not visible: {name}"


@step("The ChairLift bootc PolicyKit action requires administrator authentication")
def chairlift_bootc_policykit_requires_admin(context) -> None:
    tree = ET.parse(POLICY_FILE)
    actions = {action.get("id"): action for action in tree.getroot().findall("action")}
    assert BOOTC_ACTION_ID in actions, f"Missing action {BOOTC_ACTION_ID} in {POLICY_FILE}"
    action = actions[BOOTC_ACTION_ID]
    defaults = action.find("defaults")
    assert defaults is not None, f"Missing <defaults> for {BOOTC_ACTION_ID}"
    expected = {
        "allow_any": "auth_admin",
        "allow_inactive": "auth_admin",
        "allow_active": "auth_admin_keep",
    }
    actual = {child.tag: (child.text or "").strip() for child in defaults}
    assert actual == expected, f"Unexpected PolicyKit defaults: {actual}"
    exec_path = action.find(
        "annotate[@key='org.freedesktop.policykit.exec.path']"
    )
    assert exec_path is not None and (exec_path.text or "").strip() == str(BOOTC_HELPER), (
        f"Expected exec.path {BOOTC_HELPER}, got {exec_path.text if exec_path is not None else None}"
    )


@step("The ChairLift bootc helper executes only download-only staging")
def chairlift_bootc_helper_download_only(context) -> None:
    content = BOOTC_HELPER.read_text(encoding="utf-8")
    exec_lines = [line.strip() for line in EXEC_RE.findall(content)]
    assert len(exec_lines) == 1, f"Expected exactly one exec invocation in {BOOTC_HELPER}: {exec_lines}"
    assert exec_lines[0] == "/usr/bin/bootc upgrade --download-only", (
        f"Unexpected bootc helper exec argv: {exec_lines[0]}"
    )

"""ChairLift step definitions for the homebrew suite.

Covers Bluefin's packaging of the ChairLift managed cask: the brew-preinstall
service and managed-state contract, the system-wide desktop/icon integration
the image ships, the maintainer `config.yml` surfaced through ChairLift's own
UI, and the authenticated, stage-only bootc helper.

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

#: Desktop integration is asserted system-wide, not per-user. Homebrew has one
#: shared prefix, so the cask's ~/.local/share artifacts only ever reach the
#: FIRST user to run `brew bundle`; every later user sees the cask as already
#: installed and gets no launcher. projectbluefin/common therefore ships the
#: same upstream files under /usr, which is what these steps check. The
#: per-user copies may or may not exist depending on who provisioned the
#: prefix, so nothing here asserts them.
DESKTOP_FILE = Path("/usr/share/applications/org.frostyard.ChairLift.desktop")
ICON_DIR = Path("/usr/share/icons/hicolor")
SCALABLE_ICON = ICON_DIR / "scalable/apps/org.frostyard.ChairLift.svg"
SCALABLE_FLOWER_ICON = ICON_DIR / "scalable/apps/org.frostyard.ChairLift-flower.svg"
SYMBOLIC_ICON = ICON_DIR / "symbolic/apps/org.frostyard.ChairLift-symbolic.svg"
POLICY_FILE = Path("/usr/share/polkit-1/actions/org.frostyard.ChairLift.bootc.policy")
BOOTC_HELPER = Path("/usr/libexec/bootc-update-stage")
BOOTC_ACTION_ID = "org.frostyard.ChairLift.bootc.stage"
EXEC_RE = re.compile(r"^\s*exec\b(.*)$", re.MULTILINE)

#: The one command the privileged helper may run. Plain `bootc upgrade` queues
#: a staged deployment that ostree-finalize-staged applies at the user's next
#: ordinary shutdown, which is what ChairLift's UI reports back.
BOOTC_STAGE_ARGV = ["/usr/bin/bootc", "upgrade"]

#: Flags that must never appear, checked as whole tokens (and the `--flag=value`
#: spelling), never as substrings:
#:   --apply / --soft-reboot  reboot the machine; that is the user's decision.
#:   --download-only          bootc-upgrade(8): "it will not be applied on
#:                            reboot" -- and it re-locks a deployment uupd had
#:                            already staged for shutdown.
#:   --from-downloaded        only unlocks a prior download; never checks the
#:                            registry.
FORBIDDEN_BOOTC_FLAGS = (
    "--apply",
    "--from-downloaded",
    "--download-only",
    "--soft-reboot",
    "--reboot",
)

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

#: Reported on failure, never asserted. brew-preinstall.service carries
#: ConditionUser=!@system and ConditionPathExists=<brew binary>, so an unmet
#: condition makes systemd *skip* the unit: `start` exits 0, ActiveState stays
#: inactive, Result stays success, and only ConditionResult=no says why.
#: ExecMainStatus separates that skip from an ExecStart that ran and failed.
PREINSTALL_DIAGNOSTICS = ("ConditionResult", "ExecMainStatus")


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


def _no_root_message(state: str) -> str:
    return (
        f"ChairLift is not on the AT-SPI bus under application root "
        f"{A11Y_ROOT_NAME!r}: {state}. "
        f"Registered AT-SPI applications: {accessible_application_names()}. "
        f"The root is the binary name (g_get_prgname()), not the frame "
        f"title 'ChairLift'; an empty or unavailable list means the app "
        f"never launched or accessibility is off, not a UI regression."
    )


def _chairlift_root(context):
    """ChairLift's AT-SPI root, or an AssertionError naming what *is* registered.

    qecore's `Application.instance` is a plain attribute: `None` from
    construction until a start step assigns `get_root()`, and back to `None`
    once the app is closed (`qecore/application.py:95,338,412`). So the real
    "app absent" state is a `None` instance, not a raising lookup — reading it
    only raises when `before_all` never registered the application at all.
    Both are re-raised, never downgraded: the diagnostics add which application
    names the bus does expose, they never turn a missing root into a pass.
    """
    try:
        instance = context.chairlift.instance
    except Exception as error:  # noqa: BLE001 - re-raised as an assertion below
        raise AssertionError(
            _no_root_message(
                f"reading context.chairlift.instance raised "
                f"{type(error).__name__}: {error} — environment.before_all "
                f"never registered the application"
            )
        ) from error
    if instance is None:
        raise AssertionError(
            _no_root_message(
                "context.chairlift.instance is None — qecore assigns it from "
                "get_root() only after the app starts and resets it to None on "
                "close, so the app never launched, exited, or was closed"
            )
        )
    return instance


def _showing_named(context, name: str) -> list:
    """Visible AT-SPI nodes in ChairLift whose accessible name equals `name`."""
    return _chairlift_root(context).findChildren(
        lambda node: node.name == name and node.showing
    )


@step("The brew-preinstall user service completed successfully")
def brew_preinstall_completed(context) -> None:
    result = _run(
        "systemctl", "--user", "show", "brew-preinstall.service",
        *(f"--property={name}" for name in (*PREINSTALL_STATE, *PREINSTALL_DIAGNOSTICS)),
    )
    assert result.returncode == 0, (
        f"systemctl --user show brew-preinstall.service failed "
        f"(rc={result.returncode}): {result.stderr.strip()}"
    )
    properties = _parse_properties(result.stdout)
    actual = {name: properties.get(name) for name in PREINSTALL_STATE}
    diagnostics = {name: properties.get(name) for name in PREINSTALL_DIAGNOSTICS}
    assert actual == PREINSTALL_STATE, (
        f"brew-preinstall.service did not complete successfully: "
        f"expected {PREINSTALL_STATE}, got {actual} ({diagnostics}; "
        f"ConditionResult=no means systemd skipped the unit)"
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
    assert DESKTOP_FILE.is_file(), (
        f"Missing system-wide desktop entry {DESKTOP_FILE}. The Homebrew cask "
        f"only writes ~/.local/share/applications for the user that ran brew "
        f"bundle, so without this file every other user has no launcher."
    )
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
        assert icon.is_file() and icon.stat().st_size > 0, (
            f"Missing or empty system-wide icon: {icon}. Icon= in the desktop "
            f"entry only resolves from a system theme path for users the "
            f"cask's ~/.local/share artifacts never reach."
        )


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


@step("The ChairLift bootc helper stages the update without applying it")
def chairlift_bootc_helper_stages_only(context) -> None:
    content = BOOTC_HELPER.read_text(encoding="utf-8")
    exec_lines = [line.strip() for line in EXEC_RE.findall(content)]
    assert len(exec_lines) == 1, (
        f"Expected exactly one exec invocation in {BOOTC_HELPER}: {exec_lines}"
    )
    argv = shlex.split(exec_lines[0])

    # Name the forbidden flag first: the argv comparison below would also
    # catch it, but only as a diff of two lists.
    for flag in FORBIDDEN_BOOTC_FLAGS:
        offenders = [
            token for token in argv if token == flag or token.startswith(f"{flag}=")
        ]
        assert not offenders, (
            f"{BOOTC_HELPER} passes {flag} ({offenders}); pkexec runs this as "
            f"root and it must only stage -- never reboot, never lock "
            f"finalization, never skip the registry check"
        )

    assert argv == BOOTC_STAGE_ARGV, (
        f"Unexpected bootc helper exec argv: {argv} (expected "
        f"{BOOTC_STAGE_ARGV})"
    )

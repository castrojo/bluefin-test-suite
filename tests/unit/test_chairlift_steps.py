"""Unit tests for the homebrew suite's ChairLift steps and lane preconditions.

These cover the logic that is testable off-target: systemd property parsing,
the desktop `Exec=` realpath comparison, the bootc PolicyKit/helper contracts,
and the `before_all` preconditions that must FAIL the run rather than skip it.
"""

import os
import re
import sys
import types
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest


def _stub_modules() -> dict[str, types.ModuleType]:
    """Behave/dogtail/qecore stubs — none of them are installed in unit CI."""
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)

    qecore_stub = types.ModuleType("qecore")
    common_steps_stub = types.ModuleType("qecore.common_steps")
    common_steps_stub.__all__ = []
    sandbox_stub = types.ModuleType("qecore.sandbox")

    class _TestSandbox:  # noqa: D401 - stand-in for qecore.sandbox.TestSandbox
        def __init__(self, *args, **kwargs):
            self.applications = []

        def get_application(self, **kwargs):
            return types.SimpleNamespace(**kwargs)

    sandbox_stub.TestSandbox = _TestSandbox
    qecore_stub.common_steps = common_steps_stub
    qecore_stub.sandbox = sandbox_stub

    return {
        "behave": behave_stub,
        "qecore": qecore_stub,
        "qecore.common_steps": common_steps_stub,
        "qecore.sandbox": sandbox_stub,
    }


def _import(module_name: str):
    with patch.dict(sys.modules, _stub_modules()):
        sys.modules.pop(module_name, None)
        import importlib

        module = importlib.import_module(module_name)
    sys.modules.pop(module_name, None)
    return module


@pytest.fixture()
def steps():
    return _import("tests.homebrew.features.steps.chairlift_steps")


@pytest.fixture()
def environment():
    return _import("tests.homebrew.features.environment")


# ---------------------------------------------------------------------------
# brew-preinstall.service state — four properties, not just Result
# ---------------------------------------------------------------------------


def _show_output(**overrides: str) -> str:
    values = {
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "exited",
        "Result": "success",
        "ConditionResult": "yes",
        "ExecMainStatus": "0",
    }
    values.update(overrides)
    return "".join(f"{key}={value}\n" for key, value in values.items())


def test_parse_properties_reads_key_value_lines(steps):
    parsed = steps._parse_properties("LoadState=loaded\nResult=success\n\nbroken\n")

    assert parsed == {"LoadState": "loaded", "Result": "success"}


def test_preinstall_state_pins_all_four_properties(steps):
    assert steps.PREINSTALL_STATE == {
        "LoadState": "loaded",
        "ActiveState": "active",
        "SubState": "exited",
        "Result": "success",
    }


def test_brew_preinstall_completed_passes_on_completed_oneshot(steps):
    with patch.object(
        steps, "_run", return_value=CompletedProcess([], 0, _show_output(), "")
    ):
        steps.brew_preinstall_completed(None)


@pytest.mark.parametrize(
    ("overrides", "expected_fragment"),
    [
        # A unit that never ran still reports Result=success — the exact
        # false-positive the single-property assertion allowed.
        ({"ActiveState": "inactive", "SubState": "dead"}, "inactive"),
        ({"LoadState": "not-found"}, "not-found"),
        ({"SubState": "running"}, "running"),
        ({"Result": "exit-code"}, "exit-code"),
    ],
)
def test_brew_preinstall_completed_fails_on_bad_state(steps, overrides, expected_fragment):
    with patch.object(
        steps,
        "_run",
        return_value=CompletedProcess([], 0, _show_output(**overrides), ""),
    ):
        with pytest.raises(AssertionError) as error:
            steps.brew_preinstall_completed(None)

    assert expected_fragment in str(error.value)


def test_brew_preinstall_completed_fails_when_systemctl_fails(steps):
    with patch.object(
        steps,
        "_run",
        return_value=CompletedProcess([], 1, "", "Failed to connect to bus"),
    ):
        with pytest.raises(AssertionError, match="Failed to connect to bus"):
            steps.brew_preinstall_completed(None)


def test_brew_preinstall_failure_reports_condition_result(steps):
    """A skipped unit (unmet Condition*) looks identical without ConditionResult."""
    skipped = _show_output(
        ActiveState="inactive", SubState="dead", ConditionResult="no", ExecMainStatus=""
    )
    with patch.object(steps, "_run", return_value=CompletedProcess([], 0, skipped, "")):
        with pytest.raises(AssertionError) as error:
            steps.brew_preinstall_completed(None)

    message = str(error.value)
    assert "'ConditionResult': 'no'" in message
    assert "systemd skipped the unit" in message


def test_brew_preinstall_diagnostics_are_requested_but_never_asserted(steps):
    """ConditionResult/ExecMainStatus enrich the failure; they are not the contract."""
    assert steps.PREINSTALL_DIAGNOSTICS == ("ConditionResult", "ExecMainStatus")
    assert not set(steps.PREINSTALL_DIAGNOSTICS) & set(steps.PREINSTALL_STATE)

    captured: list[tuple[str, ...]] = []

    def _capture(*args: str):
        captured.append(args)
        return CompletedProcess([], 0, _show_output(), "")

    with patch.object(steps, "_run", _capture):
        steps.brew_preinstall_completed(None)

    requested = captured[0]
    for name in (*steps.PREINSTALL_STATE, *steps.PREINSTALL_DIAGNOSTICS):
        assert f"--property={name}" in requested


# ---------------------------------------------------------------------------
# Desktop Exec= comparison via realpath (/home vs /var/home spellings)
# ---------------------------------------------------------------------------


@pytest.fixture()
def symlinked_prefix(tmp_path: Path) -> tuple[Path, Path]:
    """Mimic a bootc image where /home is a symlink to /var/home."""
    real_bin = tmp_path / "var/home/linuxbrew/.linuxbrew/bin"
    real_bin.mkdir(parents=True)
    (real_bin / "chairlift-wrapper").write_text("#!/bin/sh\n", encoding="utf-8")
    (tmp_path / "home").symlink_to(tmp_path / "var/home")
    return tmp_path / "home/linuxbrew/.linuxbrew/bin", real_bin


def _write_desktop(tmp_path: Path, exec_line: str) -> Path:
    desktop = tmp_path / "org.frostyard.ChairLift.desktop"
    desktop.write_text(
        "[Desktop Entry]\nName=ChairLift\n" f"Exec={exec_line}\nType=Application\n",
        encoding="utf-8",
    )
    return desktop


def test_desktop_exec_accepts_symlinked_spelling(steps, tmp_path, symlinked_prefix):
    symlinked_bin, real_bin = symlinked_prefix
    desktop = _write_desktop(tmp_path, str(symlinked_bin / "chairlift-wrapper"))

    with patch.object(steps, "DESKTOP_FILE", desktop), patch.object(
        steps, "CHAIRLIFT_WRAPPER", str(real_bin / "chairlift-wrapper")
    ):
        steps.chairlift_desktop_entry_launches_wrapper(None)


def test_desktop_exec_rejects_other_binary(steps, tmp_path, symlinked_prefix):
    _, real_bin = symlinked_prefix
    desktop = _write_desktop(tmp_path, str(real_bin / "chairlift"))

    with patch.object(steps, "DESKTOP_FILE", desktop), patch.object(
        steps, "CHAIRLIFT_WRAPPER", str(real_bin / "chairlift-wrapper")
    ):
        with pytest.raises(AssertionError, match="Expected Exec to resolve to"):
            steps.chairlift_desktop_entry_launches_wrapper(None)


def test_desktop_exec_rejects_extra_arguments(steps, tmp_path, symlinked_prefix):
    _, real_bin = symlinked_prefix
    desktop = _write_desktop(tmp_path, f"{real_bin / 'chairlift-wrapper'} --update-now")

    with patch.object(steps, "DESKTOP_FILE", desktop), patch.object(
        steps, "CHAIRLIFT_WRAPPER", str(real_bin / "chairlift-wrapper")
    ):
        with pytest.raises(AssertionError, match="no extra arguments"):
            steps.chairlift_desktop_entry_launches_wrapper(None)


def test_desktop_step_reports_a_missing_system_wide_entry(steps, tmp_path):
    # The cask writes ~/.local/share/applications for the installing user
    # only, so an image that stopped shipping /usr/share/applications would
    # still "work" for whoever provisioned the Homebrew prefix and leave every
    # other user without a launcher. The step must name that, not raise
    # FileNotFoundError from read_text().
    missing = tmp_path / "absent" / "org.frostyard.ChairLift.desktop"

    with patch.object(steps, "DESKTOP_FILE", missing):
        with pytest.raises(AssertionError, match="Missing system-wide desktop entry"):
            steps.chairlift_desktop_entry_launches_wrapper(None)


def test_desktop_and_icon_paths_are_system_wide(steps):
    # Pin the contract itself: these must be /usr paths. A refactor back to
    # Path.home() would silently reduce the suite to "the first user is fine".
    assert str(steps.DESKTOP_FILE) == "/usr/share/applications/org.frostyard.ChairLift.desktop"
    for icon in (steps.SCALABLE_ICON, steps.SCALABLE_FLOWER_ICON, steps.SYMBOLIC_ICON):
        assert str(icon).startswith("/usr/share/icons/hicolor/"), icon
    assert steps.SCALABLE_ICON.name == "org.frostyard.ChairLift.svg"
    assert steps.SCALABLE_FLOWER_ICON.name == "org.frostyard.ChairLift-flower.svg"
    assert steps.SYMBOLIC_ICON.name == "org.frostyard.ChairLift-symbolic.svg"


def test_icon_step_reports_a_missing_system_wide_icon(steps, tmp_path):
    present = tmp_path / "org.frostyard.ChairLift.svg"
    present.write_text("<svg/>", encoding="utf-8")
    absent = tmp_path / "org.frostyard.ChairLift-symbolic.svg"

    with patch.object(steps, "SCALABLE_ICON", present), patch.object(
        steps, "SCALABLE_FLOWER_ICON", present
    ), patch.object(steps, "SYMBOLIC_ICON", absent):
        with pytest.raises(AssertionError, match="Missing or empty system-wide icon"):
            steps.chairlift_icons_exist(None)


def test_icon_step_rejects_an_empty_icon(steps, tmp_path):
    # A zero-byte SVG is what a broken COPY or a truncated fetch leaves
    # behind, and `is_file()` alone would pass it.
    empty = tmp_path / "org.frostyard.ChairLift.svg"
    empty.write_text("", encoding="utf-8")

    with patch.object(steps, "SCALABLE_ICON", empty), patch.object(
        steps, "SCALABLE_FLOWER_ICON", empty
    ), patch.object(steps, "SYMBOLIC_ICON", empty):
        with pytest.raises(AssertionError, match="Missing or empty system-wide icon"):
            steps.chairlift_icons_exist(None)


# ---------------------------------------------------------------------------
# bootc staging: PolicyKit defaults + a single, flagless `bootc upgrade`
# ---------------------------------------------------------------------------


POLICY_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<policyconfig>
  <action id="org.frostyard.ChairLift.bootc.stage">
    <defaults>
      <allow_any>{allow_any}</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">{exec_path}</annotate>
  </action>
</policyconfig>
"""


def _write_policy(tmp_path: Path, *, allow_any="auth_admin", exec_path="/usr/libexec/bootc-update-stage") -> Path:
    policy = tmp_path / "org.frostyard.ChairLift.bootc.policy"
    policy.write_text(
        POLICY_TEMPLATE.format(allow_any=allow_any, exec_path=exec_path), encoding="utf-8"
    )
    return policy


def test_policykit_action_requires_admin(steps, tmp_path):
    with patch.object(steps, "POLICY_FILE", _write_policy(tmp_path)):
        steps.chairlift_bootc_policykit_requires_admin(None)


def test_policykit_action_rejects_passwordless_default(steps, tmp_path):
    with patch.object(steps, "POLICY_FILE", _write_policy(tmp_path, allow_any="yes")):
        with pytest.raises(AssertionError, match="Unexpected PolicyKit defaults"):
            steps.chairlift_bootc_policykit_requires_admin(None)


def test_policykit_action_rejects_other_exec_path(steps, tmp_path):
    policy = _write_policy(tmp_path, exec_path="/usr/bin/bootc")
    with patch.object(steps, "POLICY_FILE", policy):
        with pytest.raises(AssertionError, match="Expected exec.path"):
            steps.chairlift_bootc_policykit_requires_admin(None)


def _run_helper_step(steps, tmp_path, body):
    helper = tmp_path / "bootc-update-stage"
    helper.write_text(body, encoding="utf-8")
    with patch.object(steps, "BOOTC_HELPER", helper):
        steps.chairlift_bootc_helper_stages_only(None)


@pytest.mark.parametrize(
    "body",
    [
        "#!/usr/bin/bash\nset -euo pipefail\nexec /usr/bin/bootc upgrade\n",
        # Comments naming the banned flags must not trip a substring check.
        "#!/usr/bin/bash\n# never --apply, never --download-only\n"
        "exec /usr/bin/bootc upgrade\n",
    ],
)
def test_bootc_helper_accepts_plain_upgrade(steps, tmp_path, body):
    _run_helper_step(steps, tmp_path, body)


@pytest.mark.parametrize(
    "flag",
    [
        # --apply and --soft-reboot reboot the machine.
        "--apply",
        "--soft-reboot auto",
        "--soft-reboot=auto",
        # bootc-upgrade(8) on --download-only: "it will not be applied on
        # reboot". It also re-locks a deployment uupd already staged, so
        # pressing ChairLift's button would cancel a pending update.
        "--download-only",
        # --from-downloaded only unlocks a prior download; it never checks
        # the registry, so "check for updates now" would check nothing.
        "--from-downloaded",
    ],
)
def test_bootc_helper_rejects_each_dangerous_flag(steps, tmp_path, flag):
    with pytest.raises(AssertionError, match="stages the update|passes --"):
        _run_helper_step(
            steps, tmp_path, f"#!/usr/bin/bash\nexec /usr/bin/bootc upgrade {flag}\n"
        )


@pytest.mark.parametrize(
    "flag", ["--apply", "--download-only", "--from-downloaded", "--soft-reboot=auto"]
)
def test_bootc_helper_names_the_offending_flag(steps, tmp_path, flag):
    # The exact-argv assertion alone would report a list diff. Naming the flag
    # is what tells the next reader why it is banned.
    name = flag.split("=")[0]
    with pytest.raises(AssertionError, match=f"passes {re.escape(name)}"):
        _run_helper_step(
            steps, tmp_path, f"#!/usr/bin/bash\nexec /usr/bin/bootc upgrade {flag}\n"
        )


@pytest.mark.parametrize(
    "body",
    [
        # pkexec forwards caller argv; the helper must never relay it.
        '#!/usr/bin/bash\nexec /usr/bin/bootc upgrade "$@"\n',
        # More than one exec is more than one privileged command.
        "#!/usr/bin/bash\nexec /usr/bin/bootc upgrade\nexec /usr/bin/bootc upgrade --apply\n",
        # A different binary that merely mentions the words.
        '#!/usr/bin/bash\nexec /usr/local/bin/wrapper "bootc upgrade"\n',
        # An extra subcommand is an extra privileged capability.
        "#!/usr/bin/bash\nexec /usr/bin/bootc switch ghcr.io/evil/image\n",
    ],
)
def test_bootc_helper_rejects_any_other_privileged_shape(steps, tmp_path, body):
    with pytest.raises(AssertionError):
        _run_helper_step(steps, tmp_path, body)


def test_bootc_helper_forbidden_flags_are_whole_tokens(steps, tmp_path):
    # `--apply` must not be found inside another word; the check compares
    # tokens (and the --flag=value spelling), never substrings.
    assert "--apply" in steps.FORBIDDEN_BOOTC_FLAGS
    _run_helper_step(
        steps, tmp_path, "#!/usr/bin/bash\n# --apply is banned\nexec /usr/bin/bootc upgrade\n"
    )


# ---------------------------------------------------------------------------
# Lane preconditions FAIL the run; they never become a skip
# ---------------------------------------------------------------------------


def test_environment_expected_state_agrees_with_step_assertion(environment, steps):
    """environment.py's post-start check must not drift from the step's contract."""
    shared = {
        key: value
        for key, value in steps.PREINSTALL_STATE.items()
        if key in environment.PREINSTALL_ACTIVE_STATE
    }

    assert environment.PREINSTALL_ACTIVE_STATE == shared
    assert set(environment.PREINSTALL_ACTIVE_STATE) <= set(steps.PREINSTALL_STATE)


def test_require_user_manager_raises_when_socket_unreachable(environment):
    with patch.object(
        environment,
        "_systemctl_user",
        return_value=CompletedProcess([], 1, "", "Failed to connect to bus: No such file"),
    ):
        with pytest.raises(environment.HomebrewLaneError, match="user manager unreachable"):
            environment._require_user_manager()


def test_require_user_manager_passes_when_reachable(environment):
    with patch.object(
        environment, "_systemctl_user", return_value=CompletedProcess([], 0, "257\n", "")
    ):
        environment._require_user_manager()


def test_require_user_manager_never_rewrites_runtime_dir(environment):
    """The lane needs a reachable manager, not a specific XDG_RUNTIME_DIR."""
    with patch.dict("os.environ", {"XDG_RUNTIME_DIR": "/run/user/4242"}, clear=True):
        with patch.object(
            environment, "_systemctl_user", return_value=CompletedProcess([], 0, "257\n", "")
        ):
            environment._require_user_manager()

        import os

        assert os.environ["XDG_RUNTIME_DIR"] == "/run/user/4242"


def test_require_user_manager_reports_runtime_dir_and_uid(environment):
    with patch.dict("os.environ", {"XDG_RUNTIME_DIR": "/run/user/4242"}, clear=True):
        with patch.object(
            environment, "_systemctl_user", return_value=CompletedProcess([], 1, "", "no bus")
        ):
            with pytest.raises(environment.HomebrewLaneError) as error:
                environment._require_user_manager()

    assert "/run/user/4242" in str(error.value)


def test_require_brew_binary_names_brew_setup_service(environment, tmp_path):
    with patch.object(environment, "BREW_BINARY", tmp_path / "missing/brew"):
        with pytest.raises(environment.HomebrewLaneError) as error:
            environment._require_brew_binary()

    assert "brew-setup.service" in str(error.value)


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses the X_OK check")
def test_require_brew_binary_rejects_non_executable(environment, tmp_path):
    brew = tmp_path / "brew"
    brew.write_text("#!/bin/sh\n", encoding="utf-8")
    brew.chmod(0o644)

    with patch.object(environment, "BREW_BINARY", brew):
        with pytest.raises(environment.HomebrewLaneError, match="not executable"):
            environment._require_brew_binary()


def test_require_brew_binary_passes_when_executable(environment, tmp_path):
    brew = tmp_path / "brew"
    brew.write_text("#!/bin/sh\n", encoding="utf-8")
    brew.chmod(0o755)

    with patch.object(environment, "BREW_BINARY", brew):
        environment._require_brew_binary()


def test_start_brew_preinstall_raises_on_failure(environment):
    with patch.object(
        environment,
        "_systemctl_user",
        return_value=CompletedProcess([], 1, "", "Unit brew-preinstall.service not found."),
    ):
        with pytest.raises(environment.HomebrewLaneError, match="failed to start"):
            environment._start_brew_preinstall()


def _start_then_show(show_result: CompletedProcess):
    """systemctl --user start succeeds, then `show` returns show_result."""

    def _fake(*args: str) -> CompletedProcess:
        return CompletedProcess([], 0, "", "") if args[0] == "start" else show_result

    return _fake


def test_start_brew_preinstall_asserts_unit_completed(environment):
    completed = "ActiveState=active\nSubState=exited\nResult=success\n"
    with patch.object(
        environment, "_systemctl_user", side_effect=_start_then_show(
            CompletedProcess([], 0, completed, "")
        )
    ):
        environment._start_brew_preinstall()


def test_start_brew_preinstall_rejects_zero_exit_without_completed_run(environment):
    """A `start` that returns 0 while the unit never ran must still fail."""
    never_ran = "ActiveState=inactive\nSubState=dead\nResult=success\n"
    with patch.object(
        environment, "_systemctl_user", side_effect=_start_then_show(
            CompletedProcess([], 0, never_ran, "")
        )
    ):
        with pytest.raises(environment.HomebrewLaneError, match="did not complete"):
            environment._start_brew_preinstall()


def test_start_brew_preinstall_reports_condition_result(environment):
    """ConditionUser/ConditionPathExists unmet: systemd skips the unit silently."""
    skipped = (
        "ActiveState=inactive\nSubState=dead\nResult=success\n"
        "ConditionResult=no\nExecMainStatus=\n"
    )
    with patch.object(
        environment, "_systemctl_user", side_effect=_start_then_show(
            CompletedProcess([], 0, skipped, "")
        )
    ):
        with pytest.raises(environment.HomebrewLaneError) as error:
            environment._start_brew_preinstall()

    message = str(error.value)
    assert "'ConditionResult': 'no'" in message
    assert "systemd skipped the unit" in message


def test_environment_diagnostics_match_the_step_module(environment, steps):
    """Both callers request the same non-asserted diagnostics."""
    assert environment.PREINSTALL_DIAGNOSTICS == steps.PREINSTALL_DIAGNOSTICS
    assert not set(environment.PREINSTALL_DIAGNOSTICS) & set(
        environment.PREINSTALL_ACTIVE_STATE
    )


def test_start_brew_preinstall_raises_when_state_unreadable(environment):
    with patch.object(
        environment, "_systemctl_user", side_effect=_start_then_show(
            CompletedProcess([], 1, "", "Failed to connect to bus")
        )
    ):
        with pytest.raises(environment.HomebrewLaneError, match="cannot read"):
            environment._start_brew_preinstall()


def test_before_all_requires_brew_before_starting_preinstall(environment):
    """Homebrew provisioning is checked before the unit that consumes it."""
    calls = []
    context = types.SimpleNamespace()

    with patch.object(environment, "_require_user_manager", lambda: calls.append("manager")), \
        patch.object(
            environment,
            "_require_brew_binary",
            side_effect=environment.HomebrewLaneError("no brew"),
        ), \
        patch.object(environment, "_start_brew_preinstall", lambda: calls.append("start")):
        with pytest.raises(environment.HomebrewLaneError, match="no brew"):
            environment.before_all(context)

    assert calls == ["manager"]


def test_before_all_raises_instead_of_recording_failed_setup(environment):
    context = types.SimpleNamespace()

    with patch.object(
        environment,
        "_require_user_manager",
        side_effect=environment.HomebrewLaneError("no user manager"),
    ):
        with pytest.raises(environment.HomebrewLaneError):
            environment.before_all(context)

    assert not hasattr(context, "failed_setup")
    assert context.lane_ready is False


# ---------------------------------------------------------------------------
# Launch-failure diagnostics: enrich the failure, never swallow it
# ---------------------------------------------------------------------------


class _Node:
    def __init__(self, name, showing=True):
        self.name = name
        self.showing = showing


class _Root:
    def __init__(self, nodes):
        self._nodes = nodes

    def findChildren(self, predicate):  # noqa: N802 - dogtail's API spelling
        return [node for node in self._nodes if predicate(node)]


def _context_with_root(root):
    return types.SimpleNamespace(chairlift=_QecoreApplication(root))


class _QecoreApplication:
    """qecore's Application shape: `instance` is a plain attribute, None until
    a start step assigns get_root() and None again after close."""

    def __init__(self, instance=None):
        self.instance = instance


def test_chairlift_root_returns_instance_when_present(steps):
    root = _Root([])

    assert steps._chairlift_root(_context_with_root(root)) is root


def test_chairlift_root_failure_lists_registered_applications(steps):
    """The real absent-app state is instance=None, not a raising lookup."""
    context = types.SimpleNamespace(chairlift=_QecoreApplication())

    with patch.object(
        steps, "accessible_application_names", return_value=["gnome-shell", "ptyxis"]
    ):
        with pytest.raises(AssertionError) as error:
            steps._chairlift_root(context)

    message = str(error.value)
    assert "gnome-shell" in message and "ptyxis" in message
    assert "chairlift" in message
    assert "instance is None" in message


def test_chairlift_root_failure_after_the_app_is_closed(steps):
    """qecore resets instance to None on close; that must fail, not return None."""
    application = _QecoreApplication(_Root([]))
    context = types.SimpleNamespace(chairlift=application)
    assert steps._chairlift_root(context) is application.instance

    application.instance = None
    with patch.object(steps, "accessible_application_names", return_value=[]):
        with pytest.raises(AssertionError, match="not on the AT-SPI bus"):
            steps._chairlift_root(context)


def test_chairlift_root_failure_survives_unavailable_a11y_bus(steps):
    """Diagnostics that cannot run must not replace the launch failure."""
    context = types.SimpleNamespace(chairlift=_QecoreApplication())

    with patch.object(
        steps, "accessible_application_names", return_value=["<AT-SPI unavailable: no bus>"]
    ):
        with pytest.raises(AssertionError, match="AT-SPI unavailable"):
            steps._chairlift_root(context)


def test_chairlift_root_failure_when_app_was_never_registered(steps):
    """before_all aborted, so context.chairlift itself is missing."""
    context = types.SimpleNamespace()

    with patch.object(steps, "accessible_application_names", return_value=[]):
        with pytest.raises(AssertionError, match="AttributeError"):
            steps._chairlift_root(context)


def test_ui_steps_fail_rather_than_pass_without_a_root(steps):
    """A missing root must fail every UI step, including the negative one."""
    context = types.SimpleNamespace(chairlift=_QecoreApplication())

    with patch.object(steps, "accessible_application_names", return_value=[]):
        for ui_step in (
            steps.chairlift_shows_page,
            steps.chairlift_hides_page,
            steps.chairlift_shows_group,
        ):
            with pytest.raises(AssertionError, match="not on the AT-SPI bus"):
                ui_step(context, "Applications")

        with pytest.raises(AssertionError, match="not on the AT-SPI bus"):
            steps.chairlift_has_no_configuration_error_toast(context)


def test_shows_and_hides_pages_use_visible_nodes(steps):
    context = _context_with_root(
        _Root([_Node("Applications"), _Node("Features", showing=False)])
    )

    steps.chairlift_shows_page(context, "Applications")
    steps.chairlift_hides_page(context, "Features")

    with pytest.raises(AssertionError, match="page not visible"):
        steps.chairlift_shows_page(context, "Updates")


def test_accessible_application_names_never_raises():
    from tests.shared.a11y import accessible_application_names

    with patch.dict(sys.modules, {"dogtail": None, "dogtail.tree": None}):
        names = accessible_application_names()

    assert len(names) == 1 and names[0].startswith("<AT-SPI unavailable:")


# ---------------------------------------------------------------------------
# Source-level invariants (regression guards for skipped-green setups)
# ---------------------------------------------------------------------------


def _environment_source() -> str:
    return (
        Path(__file__).resolve().parents[1] / "homebrew/features/environment.py"
    ).read_text(encoding="utf-8")


def test_environment_never_skips_on_setup_failure():
    source = _environment_source()

    assert "failed_setup" not in source
    # skip_quarantine (tag-driven) is the only sanctioned skip in this suite.
    assert "scenario.skip(" not in source


def test_environment_registers_lowercase_a11y_root(steps):
    source = _environment_source()

    assert f'a11y_app_name="{steps.A11Y_ROOT_NAME}"' in source
    assert steps.A11Y_ROOT_NAME == "chairlift"
    assert 'a11y_app_name="ChairLift"' not in source


def test_environment_never_writes_xdg_runtime_dir():
    """Relocating the runtime dir would move the a11y/session bus under qecore."""
    source = _environment_source()

    assert 'os.environ["XDG_RUNTIME_DIR"] =' not in source
    assert "os.environ.setdefault(\"XDG_RUNTIME_DIR\"" not in source
    assert "XDG_RUNTIME_DIR" in source  # still reported for diagnostics

"""Custom step definitions for Nautilus drag-and-drop spike tests."""
import os
import shlex
import subprocess
import time
import uuid
from time import sleep

from behave import step

try:
    from dogtail import tree
except Exception:  # noqa: BLE001
    tree = None  # type: ignore[assignment]
try:
    from dogtail.rawinput import absoluteMotion, drag, keyCombo, press, release
except Exception:  # noqa: BLE001
    absoluteMotion = drag = keyCombo = press = release = None  # type: ignore[misc,assignment]
try:
    from gi.repository import Atspi
except Exception:  # noqa: BLE001
    Atspi = None  # type: ignore[assignment]
try:
    from qecore.common_steps import *  # noqa: F401,F403
except Exception:  # noqa: BLE001
    pass

from app_support import _IN_CONTAINER, _ssh_args, _ssh_run


FILES_APP_NAMES = ("nautilus", "org.gnome.Nautilus", "Files")


def _skip_if_no_atspi(context) -> bool:
    if tree is None:
        try:
            context.scenario.skip("AT-SPI unavailable: dogtail not imported in this environment")
        except Exception:  # noqa: BLE001
            pass
        return True
    return False


def _nautilus_app(timeout: int = 15):
    """Find the Files app in the AT-SPI tree, retrying for up to ``timeout`` seconds."""
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        for name in FILES_APP_NAMES:
            try:
                return tree.root.application(name)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        sleep(1)
    raise AssertionError(f"GNOME Files application was not found via AT-SPI after {timeout}s: {last_error}")


def _nautilus_windows(timeout: int = 10):
    """Return all visible Files frames, retrying briefly while Nautilus settles."""
    app = _nautilus_app()
    last_children = []
    for _ in range(timeout * 2):
        frames = app.findChildren(
            lambda n: n.roleName in {"frame", "filler"}
            and n.showing
            and (n.name or "").strip() in {"Files", "Home", ""}
        )
        if frames:
            return frames
        last_children = [(child.roleName, child.name) for child in app.children[:10]]
        sleep(0.5)
    raise AssertionError(
        f"Visible Files windows not found in nautilus app. Top-level children: {last_children}"
    )


def _window_contains_file(window, filename: str) -> bool:
    """Return True if the Files window/frame contains an item named like ``filename``."""
    for _ in range(3):
        items = window.findChildren(
            lambda n: n.showing
            and n.roleName in {"list item", "icon", "push button", "label"}
            and filename in (n.name or "")
        )
        if items:
            return True
        sleep(0.2)
    return False


def _nautilus_window_for_path(path: str, marker: str, timeout: int = 10):
    """Return the Files frame that contains ``marker`` or matches ``path`` basename.

    Window titles and breadcrumb labels in GNOME 50 truncate long folder names,
    so we identify the source window by the marker file it contains and fall back
    to a basename substring match only when needed.
    """
    basename = os.path.basename(path)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            windows = _nautilus_windows(timeout=2)
        except AssertionError:
            sleep(0.5)
            continue
        for window in windows:
            if marker and _window_contains_file(window, marker):
                return window
            # Fallback: breadcrumb/label contains the basename (possibly truncated).
            if basename.lower() in (window.name or "").lower():
                return window
            for child in window.findChildren(
                lambda n: n.showing and basename[:12].lower() in (n.name or "").lower()
            )[:5]:
                return window
        sleep(0.5)
    raise AssertionError(f"No Files window found for path {path!r}")


def _vm_run(cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a shell command on the VM (SSH in container mode, local otherwise)."""
    if _IN_CONTAINER:
        return _ssh_run(cmd, timeout=timeout)
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def _vm_path_exists(path: str) -> bool:
    result = _vm_run(f"test -e {shlex.quote(path)}")
    return result.returncode == 0


def _launch_nautilus(path: str, new_window: bool = False) -> None:
    """Launch Files pointing at ``path`` on the VM session."""
    new_window_flag = " --new-window" if new_window else ""
    if _IN_CONTAINER:
        full = (
            f"source /tmp/session.env 2>/dev/null; "
            f"nohup nautilus{new_window_flag} {shlex.quote(path)} "
            f"</dev/null &>/dev/null & disown"
        )
        subprocess.run(_ssh_args() + [full], capture_output=True, text=True, timeout=15)
    else:
        cmd = ["nautilus"]
        if new_window:
            cmd.append("--new-window")
        cmd.append(path)
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _dismiss_welcome_dialog() -> None:
    """Dismiss the Bluefin first-boot Welcome dialog if it is blocking the session.

    Fresh CI VMs show a "Welcome to Bluefin" modal with Skip/Take Tour buttons.
    The dialog is either a top-level frame/dialog in gnome-shell or a separate
    application; search broadly and click Skip so subsequent AT-SPI steps can
    reach the target window.
    """
    if tree is None:
        return
    for _ in range(10):
        skip_buttons = tree.root.findChildren(
            lambda n: n.showing
            and n.roleName in {"push button", "button"}
            and (n.name or "").strip().lower() == "skip"
        )
        if not skip_buttons:
            return
        try:
            skip_buttons[0].click()
        except Exception:  # noqa: BLE001
            # Fallback: activate via AT-SPI action if the simple click fails.
            try:
                actions = skip_buttons[0].actions or {}
                for action in ("click", "press", "activate"):
                    if action in actions:
                        skip_buttons[0].do_action_named(action)
                        break
            except Exception:  # noqa: BLE001
                pass
        sleep(0.5)


@step("Source and destination directories are created with a marker file")
def source_and_destination_directories_are_created_with_a_marker_file(context) -> None:
    """Create two fresh temp dirs on the VM and a marker file in the source dir."""
    if _skip_if_no_atspi(context):
        return

    unique = uuid.uuid4().hex[:8]
    if _IN_CONTAINER:
        vm_user = os.environ.get("VM_USER", "bluefin-test")
        base = f"/home/{vm_user}/nautilus-dnd-{unique}"
    else:
        base = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), f"nautilus-dnd-{unique}")

    context.dnd_src_dir = f"{base}-src"
    context.dnd_dst_dir = f"{base}-dst"
    context.dnd_marker = f"moved-{unique}.txt"

    _vm_run(f"mkdir -p {shlex.quote(context.dnd_src_dir)} {shlex.quote(context.dnd_dst_dir)}")
    _vm_run(
        f"echo 'marker {unique}' > {shlex.quote(os.path.join(context.dnd_src_dir, context.dnd_marker))}"
    )

    assert _vm_path_exists(os.path.join(context.dnd_src_dir, context.dnd_marker)), (
        f"Marker file was not created in {context.dnd_src_dir}"
    )


@step("Files window is open for the source directory")
def files_window_is_open_for_the_source_directory(context) -> None:
    if _skip_if_no_atspi(context):
        return
    src_dir = getattr(context, "dnd_src_dir", None)
    marker = getattr(context, "dnd_marker", None)
    assert src_dir, "Source directory not set on context"
    assert marker, "Marker filename not set on context"
    _launch_nautilus(src_dir)
    sleep(2)  # D-Bus activation settle
    _dismiss_welcome_dialog()
    context.dnd_src_window = _nautilus_window_for_path(src_dir, marker=marker)
    try:
        context.dnd_src_window.click()
    except Exception:  # noqa: BLE001
        pass


def _find_destination_window(src_window, dst_dir: str, marker: str, timeout: int = 15):
    """Return a Files frame that is not ``src_window`` and points at ``dst_dir``.

    If ``nautilus --new-window`` merged into a tab or failed to open, fall back
    to opening a new window with Ctrl+N and navigating to the destination path.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            windows = _nautilus_windows(timeout=2)
        except AssertionError:
            sleep(0.5)
            continue
        for window in windows:
            if window == src_window:
                continue
            # Empty destination folder should not contain the marker.
            if marker and _window_contains_file(window, marker):
                continue
            return window
        sleep(0.5)

    # Fallback: open a new window via keyboard shortcut and navigate to dst_dir.
    try:
        src_window.click()
    except Exception:  # noqa: BLE001
        pass
    if keyCombo is not None:
        keyCombo("<Ctrl>n")
    sleep(1)
    _vm_run(
        f"source /tmp/session.env 2>/dev/null; gio open {shlex.quote(dst_dir)} &",
        timeout=5,
    )
    sleep(2)
    for _ in range(20):
        try:
            windows = _nautilus_windows(timeout=2)
        except AssertionError:
            sleep(0.5)
            continue
        for window in windows:
            if window != src_window:
                return window
        sleep(0.5)
    raise AssertionError(f"Could not open a second Files window for {dst_dir!r}")


@step("A second Files window is open for the destination directory")
def a_second_files_window_is_open_for_the_destination_directory(context) -> None:
    if _skip_if_no_atspi(context):
        return
    src_window = getattr(context, "dnd_src_window", None)
    dst_dir = getattr(context, "dnd_dst_dir", None)
    marker = getattr(context, "dnd_marker", None)
    assert src_window, "Source Files window not set on context"
    assert dst_dir, "Destination directory not set on context"
    assert marker, "Marker filename not set on context"
    _launch_nautilus(dst_dir, new_window=True)
    sleep(2)  # D-Bus activation settle
    _dismiss_welcome_dialog()
    context.dnd_dst_window = _find_destination_window(src_window, dst_dir, marker)
    try:
        context.dnd_dst_window.click()
    except Exception:  # noqa: BLE001
        pass


@step("Drag the marker file from the source Files window to the destination Files window")
def drag_the_marker_file_from_source_to_destination(context) -> None:
    if _skip_if_no_atspi(context):
        return

    marker = getattr(context, "dnd_marker", None)
    src_window = getattr(context, "dnd_src_window", None)
    dst_window = getattr(context, "dnd_dst_window", None)
    assert marker, "Marker filename not set on context"
    assert src_window, "Source Files window not set on context"
    assert dst_window, "Destination Files window not set on context"

    # Locate the source file icon by filename.
    source_node = None
    for _ in range(10):
        candidates = src_window.findChildren(
            lambda n: n.showing
            and n.roleName in {"list item", "icon", "push button", "label"}
            and marker in (n.name or "")
        )
        if candidates:
            source_node = candidates[0]
            break
        sleep(0.5)
    assert source_node, f"Marker file {marker!r} not found in source Files window"

    # Locate a suitable drop target in the destination window (file listing area or window body).
    drop_target = None
    for _ in range(5):
        candidates = dst_window.findChildren(
            lambda n: n.showing
            and n.roleName in {"list", "table", "icon", "scroll pane"}
            and len(n.children) >= 0
        )
        if candidates:
            # Prefer the largest visible container (the main content view).
            drop_target = max(candidates, key=lambda n: (n.size[0] if n.size else 0) * (n.size[1] if n.size else 0))
            break
        sleep(0.2)
    if drop_target is None:
        drop_target = dst_window

    # Re-query extents immediately before the drag to avoid stale coordinates.
    source_extents = source_node.extents
    target_extents = drop_target.extents
    src_x = source_extents.x + source_extents.width // 2
    src_y = source_extents.y + source_extents.height // 2
    dst_x = target_extents.x + target_extents.width // 2
    dst_y = target_extents.y + target_extents.height // 2

    drag_error = None
    if drag is not None:
        try:
            # On Wayland inter-window drags, dogtail's simple drag may fail; try it first
            # because it is the cleanest API when it works.
            drag((src_x, src_y), (dst_x, dst_y))
            sleep(0.5)
            return
        except Exception as exc:  # noqa: BLE001
            drag_error = exc

    # Fallback: drive the drag via explicit press / motion / release using AT-SPI events.
    if Atspi is not None:
        try:
            Atspi.generate_mouse_event(src_x, src_y, "b1p")
            # Move through several intermediate points so compositors see a trajectory.
            steps = 10
            for i in range(1, steps + 1):
                x = src_x + (dst_x - src_x) * i // steps
                y = src_y + (dst_y - src_y) * i // steps
                Atspi.generate_mouse_event(x, y, "abs")
                sleep(0.01)
            Atspi.generate_mouse_event(dst_x, dst_y, "b1r")
            sleep(0.5)
            return
        except Exception as exc:  # noqa: BLE001
            drag_error = exc

    raise AssertionError(
        f"Drag from source to destination failed. Last error: {drag_error}"
    )


@step("Select the marker file in the source Files window")
def select_the_marker_file_in_the_source_files_window(context) -> None:
    if _skip_if_no_atspi(context):
        return

    marker = getattr(context, "dnd_marker", None)
    src_window = getattr(context, "dnd_src_window", None)
    assert marker, "Marker filename not set on context"
    assert src_window, "Source Files window not set on context"

    source_node = None
    for _ in range(10):
        candidates = src_window.findChildren(
            lambda n: n.showing
            and n.roleName in {"list item", "icon", "push button", "label"}
            and marker in (n.name or "")
        )
        if candidates:
            source_node = candidates[0]
            break
        sleep(0.5)
    assert source_node, f"Marker file {marker!r} not found in source Files window"

    try:
        source_node.click()
    except Exception:  # noqa: BLE001
        # Coordinate-based fallback if AT-SPI action click is unavailable.
        extents = source_node.extents
        x = extents.x + extents.width // 2
        y = extents.y + extents.height // 2
        if Atspi is not None:
            Atspi.generate_mouse_event(x, y, "b1c")
        elif absoluteMotion is not None:
            absoluteMotion(x, y)
            if press is not None and release is not None:
                press(x, y)
                release(x, y)
    sleep(0.3)


@step("Focus the destination Files window")
def focus_the_destination_files_window(context) -> None:
    if _skip_if_no_atspi(context):
        return
    dst_window = getattr(context, "dnd_dst_window", None)
    assert dst_window, "Destination Files window not set on context"
    try:
        dst_window.click()
    except Exception:  # noqa: BLE001
        extents = dst_window.extents
        x = extents.x + extents.width // 2
        y = extents.y + extents.height // 2
        if Atspi is not None:
            Atspi.generate_mouse_event(x, y, "b1c")
    sleep(0.3)


@step("The marker file is absent from the source directory")
def the_marker_file_is_absent_from_the_source_directory(context) -> None:
    src_dir = getattr(context, "dnd_src_dir", None)
    marker = getattr(context, "dnd_marker", None)
    assert src_dir and marker, "Source directory or marker not set on context"
    path = os.path.join(src_dir, marker)
    for _ in range(10):
        if not _vm_path_exists(path):
            return
        sleep(0.5)
    raise AssertionError(f"Marker file still exists in source directory: {path}")


@step("The marker file is present in the destination directory")
def the_marker_file_is_present_in_the_destination_directory(context) -> None:
    dst_dir = getattr(context, "dnd_dst_dir", None)
    marker = getattr(context, "dnd_marker", None)
    assert dst_dir and marker, "Destination directory or marker not set on context"
    path = os.path.join(dst_dir, marker)
    for _ in range(10):
        if _vm_path_exists(path):
            return
        sleep(0.5)
    raise AssertionError(f"Marker file was not found in destination directory: {path}")


@step("Files windows are closed")
def files_windows_are_closed(context) -> None:
    """Close all Files windows and terminate the Nautilus daemon."""
    if _IN_CONTAINER:
        subprocess.run(
            _ssh_args() + ["source /tmp/session.env 2>/dev/null; nautilus --quit 2>/dev/null || true"],
            capture_output=True, text=True, timeout=10,
        )
    else:
        subprocess.run(["nautilus", "--quit"], capture_output=True, text=True, timeout=5)

    # Wait for windows to disappear from AT-SPI.
    if tree is not None:
        for _ in range(20):
            try:
                app = _nautilus_app(timeout=2)
                frames = app.findChildren(
                    lambda n: n.roleName in {"frame", "filler"} and n.showing
                )
                if not frames:
                    return
            except Exception:  # noqa: BLE001
                return
            sleep(0.5)

    # Clean up temp dirs on the VM.
    src_dir = getattr(context, "dnd_src_dir", None)
    dst_dir = getattr(context, "dnd_dst_dir", None)
    if src_dir:
        _vm_run(f"rm -rf {shlex.quote(src_dir)}")
    if dst_dir:
        _vm_run(f"rm -rf {shlex.quote(dst_dir)}")

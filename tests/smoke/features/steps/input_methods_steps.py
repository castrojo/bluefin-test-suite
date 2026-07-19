"""Input-method and keyboard-layout smoke steps."""
import shlex
import subprocess

from behave import step


def _run(cmd: str, timeout: int = 30):
    """Run a shell command locally and return stdout, returncode, stderr."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout.strip(), result.returncode, result.stderr.strip()


def _restore_input_sources(context) -> None:
    """Restore the input sources/current values captured by the save step.

    This is registered as a behave cleanup task so it runs even if a scenario
    fails mid-way. It is idempotent so an explicit ``restore original input
    sources`` step and the automatic cleanup do not fight.
    """
    state = getattr(context, "_input_methods_original_state", None)
    if not state or state.get("_restored"):
        return

    sources = state.get("sources", "")
    current = state.get("current", "")
    if sources:
        _run(
            "gsettings set org.gnome.desktop.input-sources sources "
            f"{shlex.quote(sources)}"
        )
    if current:
        _run(
            "gsettings set org.gnome.desktop.input-sources current "
            f"{shlex.quote(current)}"
        )
    state["_restored"] = True


@step("original input sources are saved for restoration")
def save_original_input_sources(context) -> None:
    """Capture the current sources/current values and register cleanup."""
    sources, src_rc, _ = _run("gsettings get org.gnome.desktop.input-sources sources")
    assert src_rc == 0, f"Failed to read input sources: {sources}"

    current, cur_rc, _ = _run("gsettings get org.gnome.desktop.input-sources current")
    assert cur_rc == 0, f"Failed to read current input source: {current}"

    context._input_methods_original_state = {
        "sources": sources,
        "current": current,
        "_restored": False,
    }
    context.add_cleanup(lambda: _restore_input_sources(context))


@step("restore original input sources")
def restore_original_input_sources(context) -> None:
    """Explicit restore step at the end of a layout-switching scenario."""
    _restore_input_sources(context)

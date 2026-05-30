"""Hardware emulation step definitions.

Generic SSH steps (Run SSH command, SSH command return code is, etc.) come from
tests/shared/ssh_steps.py via environment.py.

Only hardware-specific custom steps are defined here.
"""

from behave import step

from tests.shared.ssh_steps import run_ssh


@step("Audio output sink is detected")
def audio_output_sink_is_detected(context) -> None:
    stdout, rc = run_ssh(
        context,
        r"pactl list sinks short 2>/dev/null | grep -v 'auto_null\|dummy'",
    )
    # grep rc=0 → at least one real sink line found; rc=1 → no matches (no real sinks)
    assert rc == 0 and stdout.strip(), (
        f"No real audio sinks detected (pactl rc={rc})\n"
        f"pactl output: {stdout!r}"
    )


@step("PipeWire reports no startup errors")
def pipewire_reports_no_startup_errors(context) -> None:
    active_stdout, active_rc = run_ssh(
        context, "systemctl --user is-active pipewire.service"
    )
    assert active_rc == 0 and active_stdout.strip() == "active", (
        f"pipewire.service is not active: rc={active_rc}, output={active_stdout!r}"
    )
    journal_stdout, journal_rc = run_ssh(
        context,
        "journalctl --user -u pipewire -b --no-pager -p err 2>/dev/null",
    )
    assert journal_rc == 0, (
        f"journalctl for pipewire failed: rc={journal_rc}\n{journal_stdout}"
    )
    matches = [line for line in journal_stdout.splitlines() if "pipewire" in line.lower()]
    assert not matches, (
        "PipeWire startup errors found:\n" + "\n".join(matches)
    )

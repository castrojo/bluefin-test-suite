"""Common suite step definitions."""

from behave import step

from tests.shared.ssh_steps import *  # noqa: F401,F403


@step("Last command exits with non-zero status")
def last_command_exits_with_non_zero_status(context) -> None:
    actual = getattr(context, "ssh_rc", None)
    last_result = getattr(context, "last_ssh_result", None)
    stderr = getattr(last_result, "stderr", "") if last_result else ""
    stdout = getattr(last_result, "stdout", "") if last_result else ""
    assert actual not in (None, 0), (
        "Expected SSH command to exit non-zero\n"
        f"stdout: {stdout}\n"
        f"stderr: {stderr}"
    )

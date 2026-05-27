"""
NVIDIA variant step definitions.

Most steps are SSH command + output assertion (reuse common patterns).
TODO: Implement NVIDIA-specific steps once GPU passthrough is available.
See QA-REVIEW.md Epic E08.
"""
from behave import step


@step("Bluefin NVIDIA VM is booted and reachable over SSH")
def nvidia_vm_reachable(context):
    """Verify SSH connectivity to NVIDIA variant VM.
    TODO: Implement — same as lifecycle SSH check."""
    raise NotImplementedError("Stub — implement SSH connectivity check")


@step("SSH command output is not empty")
def output_not_empty(context):
    """Assert SSH command produced non-empty output."""
    actual = getattr(context, 'command_stdout', '') or ''
    assert actual.strip(), "SSH command output is empty"


@step('SSH command output does not contain "{text}"')
def output_does_not_contain(context, text):
    actual = getattr(context, 'command_stdout', '') or ''
    assert text not in actual, f"Output unexpectedly contains '{text}': {actual}"

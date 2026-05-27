"""
DX variant step definitions.

Most steps reuse qecore common_steps (GUI) or plain SSH steps.
Only DX-specific custom steps defined here.

TODO: Implement DX-specific steps as the variant golden disk becomes available.
See QA-REVIEW.md Epic E05.
"""
from behave import step
from qecore.common_steps import *  # noqa: F401,F403


@step('Last command output does not contain "{text}"')
def output_does_not_contain(context, text):
    """Assert last command output does NOT contain the given text."""
    actual = getattr(context, 'command_stdout', '') or ''
    assert text not in actual, f"Output unexpectedly contains '{text}': {actual}"


@step('Last command output contains "{text}"')
def output_contains(context, text):
    """Assert last command output contains the given text."""
    actual = getattr(context, 'command_stdout', '') or ''
    assert text in actual, f"Output does not contain '{text}': {actual}"

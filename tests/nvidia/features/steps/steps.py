"""
NVIDIA variant step definitions.

Most steps are SSH command + output assertion (reuse common patterns).
TODO: Implement NVIDIA-specific steps once GPU passthrough is available.
See QA-REVIEW.md Epic E08.
"""
from behave import step

from tests.shared.ssh_steps import *  # noqa: F401,F403
from tests.shared.ssh_steps import run_ssh  # noqa: F401


@step("Bluefin NVIDIA VM is booted and reachable over SSH")
def nvidia_vm_reachable(context):
    context.scenario.skip("NVIDIA GPU passthrough not yet configured — see Epic E08")

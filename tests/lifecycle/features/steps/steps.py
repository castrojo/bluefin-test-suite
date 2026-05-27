"""
Lifecycle test step definitions — bootc upgrade, rollback, switch.

Runner: plain SSH behave (no qecore/AT-SPI needed).
All steps execute commands on the VM over SSH.

TODO: Implement step definitions. These are stubs for future agents.
See QA-REVIEW.md Epic E06 for full requirements.
"""
from behave import step


@step("Bluefin VM is booted and reachable over SSH")
def vm_reachable(context):
    """Verify SSH connectivity to the test VM.
    TODO: Use context.vm_ip (set by environment.py) and SSH helper."""
    raise NotImplementedError("Stub — implement SSH connectivity check")


@step("Staged deployment is present in bootc status")
def staged_deployment_present(context):
    """Parse bootc status JSON and assert staged deployment exists.
    TODO: Parse context.command_stdout as JSON, check .staged is not null."""
    raise NotImplementedError("Stub — implement bootc status JSON parsing")


@step("Active deployment matches upgrade target digest")
def active_matches_target(context):
    """Validate the running deployment matches the expected upgrade digest.
    TODO: Compare context.expected_digest with bootc status .active.imageDigest."""
    raise NotImplementedError("Stub — implement digest comparison")


@step("Active deployment matches original image digest")
def active_matches_original(context):
    """After rollback, verify we're back on the original deployment.
    TODO: Compare with context.original_digest saved before upgrade."""
    raise NotImplementedError("Stub — implement original digest comparison")


@step('Active image reference contains "{fragment}"')
def active_image_contains(context, fragment):
    """Verify active image ref contains expected string (e.g. 'bluefin-dx').
    TODO: Parse bootc status JSON, check .active.image contains fragment."""
    raise NotImplementedError("Stub — implement image ref substring check")


@step("Reboot VM and wait for SSH")
def reboot_and_wait(context):
    """Trigger VM reboot and wait for SSH to come back.
    TODO: Either `ssh sudo reboot` + wait loop, or virtctl restart + SSH poll.
    Must handle connection drop gracefully."""
    raise NotImplementedError("Stub — implement reboot + SSH wait")


@step("ostree status shows two deployments")
def ostree_two_deployments(context):
    """Parse ostree admin status and verify exactly 2 deployments listed.
    TODO: Count lines matching deployment marker in ostree output."""
    raise NotImplementedError("Stub — implement ostree deployment count")

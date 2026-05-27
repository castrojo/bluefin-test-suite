"""
Security test step definitions — cosign verification, SELinux checks.

TODO: Implement step definitions. These are stubs for future agents.
See QA-REVIEW.md Epics E03 (cosign) and E04 (SELinux) for requirements.
"""
import subprocess

from behave import step


@step('Verify cosign signature for "{image}"')
def verify_cosign_signature(context, image):
    """Run cosign verify against the given image with OIDC constraints.
    TODO: Implement — shell out to cosign CLI with proper flags."""
    raise NotImplementedError("Stub — implement cosign verify invocation")


@step('Verify cosign signature for "{image}" expecting failure')
def verify_cosign_failure(context, image):
    """Verify that cosign fails for an unsigned image.
    TODO: Implement — run cosign verify, assert non-zero exit."""
    raise NotImplementedError("Stub — implement cosign verify failure case")


@step('Signature OIDC issuer is "{issuer}"')
def signature_oidc_issuer(context, issuer):
    """Assert that the verified signature's OIDC issuer matches.
    TODO: Parse cosign verify output for certificate issuer field."""
    raise NotImplementedError("Stub — implement OIDC issuer assertion")


@step('Signature identity matches "{pattern}"')
def signature_identity_matches(context, pattern):
    """Assert that the certificate identity matches the expected regex.
    TODO: Parse cosign verify output for certificate identity."""
    raise NotImplementedError("Stub — implement identity regex assertion")


@step("Verification error message is clear and actionable")
def verification_error_clear(context):
    """Assert failure output includes a useful error message.
    TODO: Check context.last_error contains cosign-specific guidance."""
    raise NotImplementedError("Stub — implement error message validation")

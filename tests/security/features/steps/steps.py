"""
Security test step definitions — cosign verification, SELinux checks.
"""
import json
import re
import subprocess

from behave import step

from tests.shared.ssh_steps import *  # noqa: F401,F403


def _run_cosign_verify(context, image):
    result = subprocess.run(
        [
            "cosign",
            "verify",
            "--certificate-oidc-issuer",
            context.cosign_issuer or "https://token.actions.githubusercontent.com",
            "--certificate-identity-regexp",
            context.cosign_identity or "https://github.com/ublue-os/.*",
            "--output",
            "json",
            image,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    context.cosign_output = result.stdout
    context.cosign_error = result.stderr
    return result


def _cosign_entries(context):
    raw = getattr(context, "cosign_output", None)
    assert raw, "No cosign output available"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Invalid cosign JSON output: {exc}\n{raw}") from exc

    if isinstance(payload, list):
        assert payload, "cosign output JSON array is empty"
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise AssertionError(f"Unexpected cosign JSON payload type: {type(payload).__name__}")


def _collect_values(value, keys):
    matches = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in keys:
                if isinstance(nested, list):
                    matches.extend(str(item) for item in nested if item is not None)
                elif nested is not None:
                    matches.append(str(nested))
            matches.extend(_collect_values(nested, keys))
    elif isinstance(value, list):
        for item in value:
            matches.extend(_collect_values(item, keys))
    return matches


@step('Cosign certificate issuer is "{issuer}" and identity pattern is "{pattern}"')
def set_cosign_issuer_identity(context, issuer, pattern):
    """Configure OIDC issuer and identity pattern before calling Verify cosign signature."""
    context.cosign_issuer = issuer
    context.cosign_identity = pattern


@step('Verify cosign signature for "{image}"')
def verify_cosign_signature(context, image):
    """Run cosign verify against the given image with OIDC constraints."""
    result = _run_cosign_verify(context, image)
    assert result.returncode == 0, f"cosign verify failed for {image}:\n{result.stderr}"


@step('Verify cosign signature for "{image}" expecting failure')
def verify_cosign_failure(context, image):
    """Verify that cosign fails for an unsigned image."""
    result = _run_cosign_verify(context, image)
    assert result.returncode != 0, f"Expected cosign verify to fail for {image}"


@step('Signature OIDC issuer is "{issuer}"')
def signature_oidc_issuer(context, issuer):
    """Assert that the verified signature's OIDC issuer matches."""
    entry = _cosign_entries(context)[0]
    certificate = entry.get("certificate") or entry.get("Certificate") or {}
    actual = None
    if isinstance(certificate, dict):
        actual = certificate.get("Issuer") or certificate.get("issuer")
    if actual is None:
        issuers = _collect_values(entry, {"Issuer", "issuer"})
        actual = issuers[0] if issuers else None

    assert actual == issuer, f"Expected OIDC issuer '{issuer}', got '{actual}'"


@step('Signature identity matches "{pattern}"')
def signature_identity_matches(context, pattern):
    """Assert that the certificate identity matches the expected regex."""
    entry = _cosign_entries(context)[0]
    identities = _collect_values(
        entry,
        {"SubjectAlternativeName", "subjectAlternativeName", "identity"},
    )
    assert identities, f"No signature identity fields found in cosign output: {entry}"
    assert any(re.search(pattern, identity) for identity in identities), (
        f"No signature identity matched '{pattern}'. Candidates: {identities}"
    )


@step("Verification error message is clear and actionable")
def verification_error_clear(context):
    """Assert failure output includes a useful error message."""
    error = getattr(context, "cosign_error", "") or ""
    assert error.strip(), "Expected cosign verification to produce an error message"

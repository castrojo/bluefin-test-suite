@security @cosign @preflight
Feature: Container image signature verification
  Validates that Bluefin images are correctly signed by the upstream build
  systems (projectbluefin and ublue-os GitHub Actions).
  Runner: plain SSH or local (cosign CLI needed).

  # This does NOT replicate signing infrastructure.
  # The build systems sign; we only verify the signatures are sound.
  # See QA-REVIEW.md Epic E03 for full design.

  # ── projectbluefin images ──────────────────────────────────────────────────

  @cosign @projectbluefin @pb_bluefin_latest
  Scenario: projectbluefin Bluefin latest image has valid cosign signature
    * Cosign certificate issuer is "https://token.actions.githubusercontent.com" and identity pattern is "https://github.com/projectbluefin/.*"
    * Verify cosign signature for "ghcr.io/projectbluefin/bluefin:latest"
    * Signature OIDC issuer is "https://token.actions.githubusercontent.com"
    * Signature identity matches "https://github.com/projectbluefin/.*"

  @cosign @projectbluefin @pb_bluefin_lts
  Scenario: projectbluefin Bluefin LTS image has valid cosign signature
    * Cosign certificate issuer is "https://token.actions.githubusercontent.com" and identity pattern is "https://github.com/projectbluefin/.*"
    * Verify cosign signature for "ghcr.io/projectbluefin/bluefin:lts"
    * Signature OIDC issuer is "https://token.actions.githubusercontent.com"
    * Signature identity matches "https://github.com/projectbluefin/.*"

  @cosign @projectbluefin @pb_dakota_latest
  Scenario: projectbluefin Dakota latest image has valid cosign signature
    * Cosign certificate issuer is "https://token.actions.githubusercontent.com" and identity pattern is "https://github.com/projectbluefin/.*"
    * Verify cosign signature for "ghcr.io/projectbluefin/dakota:latest"
    * Signature OIDC issuer is "https://token.actions.githubusercontent.com"
    * Signature identity matches "https://github.com/projectbluefin/.*"

  # ── ublue-os images ────────────────────────────────────────────────────────

  @cosign @bluefin_latest
  Scenario: Bluefin latest image has valid cosign signature
    * Cosign certificate issuer is "https://token.actions.githubusercontent.com" and identity pattern is "https://github.com/ublue-os/.*"
    * Verify cosign signature for "ghcr.io/ublue-os/bluefin:latest"
    * Signature OIDC issuer is "https://token.actions.githubusercontent.com"
    * Signature identity matches "https://github.com/ublue-os/.*"

  @cosign @bluefin_lts
  Scenario: Bluefin LTS image has valid cosign signature
    * Cosign certificate issuer is "https://token.actions.githubusercontent.com" and identity pattern is "https://github.com/ublue-os/.*"
    * Verify cosign signature for "ghcr.io/ublue-os/bluefin:lts"
    * Signature OIDC issuer is "https://token.actions.githubusercontent.com"
    * Signature identity matches "https://github.com/ublue-os/.*"

  @cosign @bluefin_dx
  Scenario: Bluefin DX image has valid cosign signature
    * Cosign certificate issuer is "https://token.actions.githubusercontent.com" and identity pattern is "https://github.com/ublue-os/.*"
    * Verify cosign signature for "ghcr.io/ublue-os/bluefin-dx:latest"
    * Signature OIDC issuer is "https://token.actions.githubusercontent.com"
    * Signature identity matches "https://github.com/ublue-os/.*"

  @cosign @bluefin_nvidia
  Scenario: Bluefin NVIDIA image has valid cosign signature
    * Cosign certificate issuer is "https://token.actions.githubusercontent.com" and identity pattern is "https://github.com/ublue-os/.*"
    * Verify cosign signature for "ghcr.io/ublue-os/bluefin-nvidia:latest"
    * Signature OIDC issuer is "https://token.actions.githubusercontent.com"
    * Signature identity matches "https://github.com/ublue-os/.*"

  @cosign @negative
  Scenario: Unsigned image fails verification gracefully
    * Verify cosign signature for "docker.io/library/busybox:latest" expecting failure
    * Verification error message is clear and actionable

  @cosign @bluefin_gts
  Scenario: Bluefin GTS stream image has valid cosign signature
    * Cosign certificate issuer is "https://token.actions.githubusercontent.com" and identity pattern is "https://github.com/ublue-os/.*"
    * Verify cosign signature for "ghcr.io/ublue-os/bluefin:gts"
    * Signature OIDC issuer is "https://token.actions.githubusercontent.com"
    * Signature identity matches "https://github.com/ublue-os/.*"

  @cosign @bluefin_dx_nvidia
  Scenario: Bluefin DX NVIDIA image has valid cosign signature
    * Cosign certificate issuer is "https://token.actions.githubusercontent.com" and identity pattern is "https://github.com/ublue-os/.*"
    * Verify cosign signature for "ghcr.io/ublue-os/bluefin-dx-nvidia:latest"
    * Signature OIDC issuer is "https://token.actions.githubusercontent.com"
    * Signature identity matches "https://github.com/ublue-os/.*"

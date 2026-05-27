# bluefin-test-suite Justfile
# All commands go through here — no loose shell commands.

image     := env_var_or_default("BLUEFIN_IMAGE", "ghcr.io/ublue-os/bluefin:latest")
image_tag := env_var_or_default("BLUEFIN_IMAGE_TAG", "latest")
namespace := "bluefin-test"
argo_ns   := "argo"

# List all available recipes
default:
    @just --list

# ── Prerequisites ────────────────────────────────────────────────────────────

# Install CDI (Containerized Data Importer) — run once before first test
install-cdi:
    argo submit --from workflowtemplate/install-cdi -n {{ argo_ns }} --watch

# Apply CDI insecure registry config for ghost:5000
configure-cdi:
    kubectl apply -f manifests/cdi-insecure-registry.yaml

# Generate SSH keypair and store in cluster (idempotent)
setup-ssh-secret:
    #!/usr/bin/env bash
    set -euo pipefail
    if kubectl get secret bluefin-test-ssh-key -n {{ argo_ns }} &>/dev/null; then
        echo "✓ bluefin-test-ssh-key already exists"
        exit 0
    fi
    ssh_key=".bluefin-test-key"
    ssh-keygen -t ed25519 -f "${ssh_key}" -N "" -C "bluefin-test-suite@ghost"
    kubectl create secret generic bluefin-test-ssh-key \
        --from-file=id_ed25519="${ssh_key}" \
        --from-file=id_ed25519.pub="${ssh_key}.pub" \
        -n {{ argo_ns }}
    echo "BLUEFIN_TEST_PUBKEY=$(cat "${ssh_key}.pub")" > .env.test-pubkey
    shred -u "${ssh_key}" "${ssh_key}.pub"
    echo "✓ SSH secret created — source .env.test-pubkey before running tests"

# Apply all WorkflowTemplates to the cluster
apply-templates:
    @for f in argo/workflow-templates/*.yaml; do \
        echo "Applying $$f..."; \
        kubectl apply -f $$f -n {{ argo_ns }}; \
    done

# One-time cluster setup: CDI + RBAC + templates + SSH secret
setup-cluster:
    just install-cdi
    just configure-cdi
    just apply-templates
    just setup-ssh-secret

# ── Disk image management ────────────────────────────────────────────────────

# Pre-build disk image for a given tag and push to ghost zot (idempotent)
# Usage: just ensure-disk            → uses BLUEFIN_IMAGE / BLUEFIN_IMAGE_TAG
# Usage: just ensure-disk ghcr.io/ublue-os/bluefin:gts gts
ensure-disk img=image tag=image_tag:
    argo submit --from workflowtemplate/bib-build-and-push \
        -p image="{{ img }}" \
        -p image-tag="{{ tag }}" \
        -n {{ argo_ns }} \
        --watch

# List disk images currently in ghost zot
list-disks:
    skopeo list-tags --tls-verify=false docker://192.168.1.102:5000/bluefin-disk 2>/dev/null \
        || echo "(no bluefin-disk images in zot yet)"

# ── Test execution ───────────────────────────────────────────────────────────

# Run smoke tests. Requires: source .env.test-pubkey first.
# Usage: just run-tests
run-tests:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    argo submit argo/bluefin-smoke-test.yaml \
        -p image="{{ image }}" \
        -p image-tag="{{ image_tag }}" \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -n {{ argo_ns }} \
        --watch

# Run tests against a specific image
# Usage: just run-tests-image ghcr.io/ublue-os/bluefin:gts gts
run-tests-image img tag:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    argo submit argo/bluefin-smoke-test.yaml \
        -p image="{{ img }}" \
        -p image-tag="{{ tag }}" \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -n {{ argo_ns }} \
        --watch

# Run matrix tests (latest + lts in parallel). Optional: PR_TITLE, PR_NUMBER env vars.
run-tests-matrix:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    PR_TITLE="${PR_TITLE:-}"
    PR_NUMBER="${PR_NUMBER:-}"
    argo submit argo/bluefin-test-matrix.yaml \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -p pr-title="${PR_TITLE}" \
        -p pr-number="${PR_NUMBER}" \
        -n {{ argo_ns }} \
        --watch

# Run smoke against persistent titan VMs (no BIB build, instant start).
# Looks up titan-bluefin and titan-lts IPs live from the cluster.
# Usage: just run-titan-smoke
run-titan-smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    IP_LATEST=$(kubectl get vmi titan-bluefin -n bluefin-test \
        -o jsonpath='{.status.interfaces[0].ipAddress}' 2>/dev/null)
    IP_LTS=$(kubectl get vmi titan-lts -n bluefin-lts-test \
        -o jsonpath='{.status.interfaces[0].ipAddress}' 2>/dev/null)
    : "${IP_LATEST:?titan-bluefin VMI not found or has no IP}"
    : "${IP_LTS:?titan-lts VMI not found or has no IP}"
    echo "titan-bluefin: ${IP_LATEST}"
    echo "titan-lts:     ${IP_LTS}"
    argo submit --from workflowtemplate/bluefin-titan-smoke \
        -p vm-ip-latest="${IP_LATEST}" \
        -p vm-ip-lts="${IP_LTS}" \
        -n {{ argo_ns }} \
        --watch

# Run Flatcar smoke tests
run-flatcar-smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    argo submit argo/flatcar-smoke-test.yaml \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -n {{ argo_ns }} \
        --watch

# Run DX variant smoke tests (requires DX golden disk)
run-dx-smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    argo submit argo/bluefin-smoke-test.yaml \
        -p image="ghcr.io/ublue-os/bluefin-dx:latest" \
        -p image-tag="dx-latest" \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -n {{ argo_ns }} \
        --watch

# Run lifecycle tests (bootc upgrade/rollback) — requires upgrade target image
run-lifecycle:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    argo submit argo/bluefin-smoke-test.yaml \
        -p image="{{ image }}" \
        -p image-tag="{{ image_tag }}" \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -p suite="lifecycle" \
        -n {{ argo_ns }} \
        --watch

# Run security tests (cosign + SELinux) — requires selinux=0 removed from golden disks
run-security:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    argo submit argo/bluefin-smoke-test.yaml \
        -p image="{{ image }}" \
        -p image-tag="{{ image_tag }}" \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -p suite="security" \
        -n {{ argo_ns }} \
        --watch

# Run vanilla GNOME baseline tests (nightly comparison)
run-vanilla-gnome:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    argo submit argo/bluefin-smoke-test.yaml \
        -p image="quay.io/fedora/fedora-bootc:latest" \
        -p image-tag="vanilla-gnome" \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -p suite="vanilla-gnome" \
        -n {{ argo_ns }} \
        --watch

# ── Observation ─────────────────────────────────────────────────────────────

# List all test workflows
list-workflows:
    argo list -n {{ argo_ns }}

# Tail logs from the most recent test workflow
logs:
    argo logs -n {{ argo_ns }} @latest

# List VMs in the test namespace
list-vms:
    kubectl get vm -n {{ namespace }}

# List PVCs in the test namespace
list-pvcs:
    kubectl get pvc -n {{ namespace }}

# ── Build ────────────────────────────────────────────────────────────────────

# Build the tmt runner container image
build-runner:
    podman build -f container/Containerfile -t localhost/bluefin-tmt-runner:latest .

# Push runner image to ghost zot registry
push-runner:
    podman push localhost/bluefin-tmt-runner:latest \
        192.168.1.102:5000/bluefin-tmt-runner:latest \
        --tls-verify=false

# ── Cleanup ──────────────────────────────────────────────────────────────────

# Delete all VMs in the test namespace
delete-vms:
    kubectl delete vm --all -n {{ namespace }} || true

# Delete all PVCs in the test namespace (preserves base disk images in zot)
delete-pvcs:
    kubectl delete pvc --all -n {{ namespace }} || true

# Delete all test workflows
delete-workflows:
    argo delete --all -n {{ argo_ns }} || true

# Full teardown of in-flight resources (keeps zot disk images)
teardown:
    just delete-vms
    just delete-pvcs
    just delete-workflows

# ── Validation ───────────────────────────────────────────────────────────────

# Lint all Argo YAML manifests
lint:
    @for f in argo/*.yaml argo/workflow-templates/*.yaml; do \
        echo "Linting $$f..."; \
        argo lint $$f || exit 1; \
    done
    @echo "✓ All manifests valid"

# Validate tmt plans and tests
validate-tmt:
    tmt plans show
    tmt tests show

# Verify cosign signatures on all active Bluefin image tags
verify-images:
    #!/usr/bin/env bash
    set -euo pipefail
    IMAGES=(
        "ghcr.io/ublue-os/bluefin:latest"
        "ghcr.io/ublue-os/bluefin:lts"
        # Uncomment as variants are added to the matrix:
        # "ghcr.io/ublue-os/bluefin-dx:latest"
        # "ghcr.io/ublue-os/bluefin-nvidia:latest"
    )
    ISSUER="https://token.actions.githubusercontent.com"
    IDENTITY="https://github.com/ublue-os/.*"
    FAILED=0
    for img in "${IMAGES[@]}"; do
        echo "Verifying: ${img}..."
        if cosign verify \
            --certificate-oidc-issuer="${ISSUER}" \
            --certificate-identity-regexp="${IDENTITY}" \
            "${img}" >/dev/null 2>&1; then
            echo "  ✓ ${img}"
        else
            echo "  ✗ ${img} — signature verification FAILED"
            FAILED=$((FAILED + 1))
        fi
    done
    if [[ ${FAILED} -gt 0 ]]; then
        echo "ERROR: ${FAILED} image(s) failed verification"
        exit 1
    fi
    echo "✓ All images verified"

# List all stub/future test scenarios not yet implemented
list-stubs:
    #!/usr/bin/env bash
    echo "=== Stubbed scenarios (@future tag) ==="
    grep -r '@future' tests/*/features/*.feature 2>/dev/null | sed 's/.*tests/  tests/' || echo "  (none)"
    echo ""
    echo "=== NotImplementedError stubs ==="
    grep -rn 'raise NotImplementedError' tests/*/features/steps/*.py 2>/dev/null | sed 's/.*tests/  tests/' || echo "  (none)"

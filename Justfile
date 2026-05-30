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
        echo "Applying $f..."; \
        kubectl apply -f $f -n {{ argo_ns }}; \
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

# Run DX variant tests (smoke + dx suite). Requires DX golden disk.
# Builds DX golden disk if not present (~100s cold BIB).
run-dx-smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    argo submit argo/bluefin-dx-test.yaml \
        -p image="ghcr.io/ublue-os/bluefin-dx:latest" \
        -p image-tag="dx-latest" \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -n {{ argo_ns }} \
        --watch

# Run lifecycle tests (bootc upgrade/rollback/switch).
# runner-type=plain-ssh; step defs handle SSH reconnect after reboot.
run-lifecycle:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    argo submit argo/bluefin-lifecycle-test.yaml \
        -p image="{{ image }}" \
        -p image-tag="{{ image_tag }}" \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
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
        -p runner-type="plain-ssh" \
        -n {{ argo_ns }} \
        --watch

# Run hardware device emulation tests (TPM, audio, watchdog) — uses full-hw VM profile
run-hardware-tests:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    argo submit argo/bluefin-smoke-test.yaml \
        -p image="{{ image }}" \
        -p image-tag="{{ image_tag }}" \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -p suite="hardware" \
        -p runner-type="plain-ssh" \
        -p hw-profile="full-hw" \
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
        -p runner-type="qecore" \
        -n {{ argo_ns }} \
        --watch

# ── Results ──────────────────────────────────────────────────────────────────

# Targets: results, results-timing, clean-results
# List recent test results stored on ghost (most recent first)
# Usage: just results            → last 10 runs
# Usage: just results 20         → last 20 runs
results n="10":
    #!/usr/bin/env bash
    set -euo pipefail
    BASE="/var/tmp/bluefin-results"
    if [[ ! -d "${BASE}" ]]; then
        echo "(no results yet — run a test first)"
        exit 0
    fi
    echo "=== Recent test results (last {{ n }}) ==="
    COUNT=0
    for dir in $(ls -1t "${BASE}"); do
        [[ ${COUNT} -ge {{ n }} ]] && break
        RUN="${BASE}/${dir}"
        echo ""
        echo "Run: ${dir}"
        for suite_dir in "${RUN}"/*/; do
            SUITE=$(basename "${suite_dir}")
            JSON="${suite_dir}results.json"
            if [[ -f "${JSON}" ]]; then
                python3 -c "
    import json
    try:
        data = json.load(open('${JSON}'))
        failed = sum(1 for f in data for s in f.get('elements',[]) if s.get('status') == 'failed')
        total  = sum(len(f.get('elements',[])) for f in data)
        icon = '✓' if failed == 0 else '✗'
        print(f'  {icon} ${SUITE}: {total - failed}/{total} passed')
    except Exception as e:
        print(f'  ? ${SUITE}: (error reading results.json: {e})')
    " 2>/dev/null
            else
                echo "  ? ${SUITE}: (no results.json)"
            fi
        done
        COUNT=$((COUNT + 1))
    done

# Show per-scenario timing table from the most recent run (or a specific run-uid)
# Usage: just results-timing          → most recent run
# Usage: just results-timing <uid>    → specific run
results-timing uid="":
    #!/usr/bin/env bash
    set -euo pipefail
    BASE="${RESULTS_BASE:-/var/tmp/bluefin-results}"
    if [[ -z "{{ uid }}" ]]; then
        RUN_ID=$(ls -1t "${BASE}" 2>/dev/null | head -1)
        [[ -z "${RUN_ID}" ]] && echo "(no results yet)" && exit 0
        RUN="${BASE}/${RUN_ID}"
    else
        RUN="${BASE}/{{ uid }}"
    fi
    if [[ ! -d "${RUN}" ]]; then
        echo "(run not found: ${RUN})"
        exit 1
    fi
    RUN="${RUN}" python3 <<'PYEOF'
    import json
    import os
    import sys
    from pathlib import Path

    run = Path(os.environ["RUN"])
    strict = os.environ.get("TIMING_SLA_STRICT", "").lower() in {"1", "true", "yes"}
    rows = []
    for path in sorted(run.rglob("timings.jsonl")):
        suite = path.parent.name
        with path.open(encoding="utf-8") as file_obj:
            for line in file_obj:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                rows.append({
                    "suite": suite,
                    "scenario": str(entry.get("scenario", "")),
                    "status": str(entry.get("status", "unknown")),
                    "elapsed": float(entry.get("elapsed_s", 0.0)),
                    "sla": entry.get("sla_s", "-"),
                    "violation": "yes" if entry.get("sla_violated") else "no",
                })

    if not rows:
        print("(no timing data found in %s)" % run)
        sys.exit(0)

    rows.sort(key=lambda row: row["elapsed"], reverse=True)
    headers = [("Suite", "suite"), ("Scenario", "scenario"), ("Status", "status"), ("Elapsed", "elapsed"), ("SLA", "sla"), ("Violation", "violation")]
    formatted = []
    for row in rows:
        formatted.append({
            **row,
            "elapsed": "%.3fs" % row["elapsed"],
            "sla": "%ss" % row["sla"],
        })
    widths = {title: len(title) for title, _ in headers}
    for row in formatted:
        for title, key in headers:
            widths[title] = max(widths[title], len(str(row[key])))

    header_line = " | ".join(title.ljust(widths[title]) for title, _ in headers)
    rule_line = "-+-".join("-" * widths[title] for title, _ in headers)
    print(header_line)
    print(rule_line)
    for row in formatted:
        print(" | ".join(str(row[key]).ljust(widths[title]) for title, key in headers))

    violations = sum(1 for row in rows if row["violation"] == "yes")
    print()
    print("Total scenarios timed: %d" % len(rows))
    print("SLA violations: %d" % violations)
    if strict and violations:
        sys.exit(1)
    PYEOF
# Remove old test results from ghost hostPath (keeps last N runs)
# Usage: just clean-results      → keep last 20 runs
# Usage: just clean-results 5    → keep last 5 runs
clean-results keep="20":
    #!/usr/bin/env bash
    set -euo pipefail
    BASE="/var/tmp/bluefin-results"
    if [[ ! -d "${BASE}" ]]; then
        echo "(no results directory)"
        exit 0
    fi
    TOTAL=$(ls -1 "${BASE}" | wc -l)
    TO_DELETE=$((TOTAL - {{ keep }}))
    if [[ ${TO_DELETE} -le 0 ]]; then
        echo "✓ ${TOTAL} runs present, nothing to remove (keeping {{ keep }})"
        exit 0
    fi
    echo "Removing ${TO_DELETE} oldest run(s) (keeping {{ keep }} of ${TOTAL})..."
    ls -1t "${BASE}" | tail -${TO_DELETE} | while read dir; do
        echo "  removing ${BASE}/${dir}"
        rm -rf "${BASE:?}/${dir}"
    done
    echo "✓ Done"

# Compare overlapping scenarios between smoke and vanilla-gnome results
# Usage: just compare-results
# Usage: just compare-results <run-uid>
compare-results run_uid="":
    #!/usr/bin/env bash
    set -euo pipefail
    BASE="/var/tmp/bluefin-results"
    if [[ ! -d "${BASE}" ]]; then
        echo "(no results directory — run a test first)"
        exit 0
    fi
    if [[ -n "{{ run_uid }}" ]]; then
        RUN_DIR="${BASE}/{{ run_uid }}"
        if [[ ! -d "${RUN_DIR}" ]]; then
            echo "(run not found: {{ run_uid }})"
            exit 0
        fi
    else
        LATEST=$(ls -1t "${BASE}" | head -1)
        if [[ -z "${LATEST}" ]]; then
            echo "(no results yet — run a test first)"
            exit 0
        fi
        RUN_DIR="${BASE}/${LATEST}"
    fi
    SMOKE_JSON="${RUN_DIR}/smoke/results.json"
    VANILLA_JSON="${RUN_DIR}/vanilla-gnome/results.json"
    if [[ ! -f "${SMOKE_JSON}" || ! -f "${VANILLA_JSON}" ]]; then
        echo "(comparison skipped — expected smoke/results.json and vanilla-gnome/results.json under ${RUN_DIR})"
        exit 0
    fi
    RUN_UID=$(basename "${RUN_DIR}")
    RUN_UID="${RUN_UID}" SMOKE_JSON="${SMOKE_JSON}" VANILLA_JSON="${VANILLA_JSON}" python3 - <<'PY'
        import json
        import os
        import sys
        from pathlib import Path


        def load_statuses(path: str) -> dict[str, str]:
            data = json.loads(Path(path).read_text())
            statuses: dict[str, str] = {}
            for feature in data:
                for element in feature.get("elements", []):
                    if element.get("type") != "scenario":
                        continue
                    name = element.get("name")
                    if name:
                        statuses[name] = element.get("status", "unknown")
            return statuses


        run_uid = os.environ["RUN_UID"]
        smoke = load_statuses(os.environ["SMOKE_JSON"])
        vanilla = load_statuses(os.environ["VANILLA_JSON"])
        overlap = sorted(set(smoke) & set(vanilla))

        print(f"=== Smoke vs Vanilla-GNOME comparison: {run_uid} ===")
        if not overlap:
            print("(no overlapping scenarios found)")
            sys.exit(0)

        scenario_width = max(len("Scenario"), *(len(name) for name in overlap))
        smoke_width = max(len("Smoke"), *(len(smoke[name]) for name in overlap))
        vanilla_width = max(len("Vanilla-GNOME"), *(len(vanilla[name]) for name in overlap))

        header = f"{'Scenario':<{scenario_width}}  {'Smoke':<{smoke_width}}  {'Vanilla-GNOME':<{vanilla_width}}"
        print(header)
        print(f"{'-' * scenario_width}  {'-' * smoke_width}  {'-' * vanilla_width}")

        bluefin_regressions = 0
        upstream_issues = 0
        same_result = 0
        for name in overlap:
            smoke_status = smoke[name]
            vanilla_status = vanilla[name]
            note = ""
            if smoke_status == "failed" and vanilla_status == "passed":
                bluefin_regressions += 1
                note = "  ⚠ Bluefin regression"
            elif smoke_status == "failed" and vanilla_status == "failed":
                upstream_issues += 1
                note = "  ↑ Upstream GNOME issue"
            else:
                same_result += 1
            print(f"{name:<{scenario_width}}  {smoke_status:<{smoke_width}}  {vanilla_status:<{vanilla_width}}{note}")

        print(
            f"Summary: {len(overlap)} overlapping scenario(s) | "
            f"{bluefin_regressions} Bluefin regression(s) | "
            f"{upstream_issues} upstream GNOME issue(s) | "
            f"{same_result} other matching/mixed result(s)"
        )
    PY

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
# "template reference not found" errors are expected for Workflow files that
# reference cluster-deployed WorkflowTemplates — argo lint can't resolve them
# without a live cluster connection.  We only fail on real YAML/schema errors.
lint:
    #!/usr/bin/env bash
    set -uo pipefail
    ERRORS=0
    for f in argo/*.yaml argo/workflow-templates/*.yaml; do
        echo "Linting ${f}..."
        OUTPUT=$(argo lint "${f}" 2>&1) || true
        if echo "${OUTPUT}" | grep -q '✖'; then
            # Ignore expected "template reference not found" and count-summary lines.
            # Real errors: ✖ lines that aren't cross-template ref warnings or summaries.
            REAL_ERRORS=$(echo "${OUTPUT}" | grep '✖' \
                | grep -v 'template reference.*not found' \
                | grep -v 'linting errors found' || true)
            if [[ -n "${REAL_ERRORS}" ]]; then
                echo "${OUTPUT}"
                ERRORS=$((ERRORS + 1))
            else
                echo "  (ok — only expected external templateRef warnings)"
            fi
        fi
    done
    if [[ ${ERRORS} -gt 0 ]]; then
        echo "✖ ${ERRORS} real linting error(s) found"
        exit 1
    fi
    echo "✓ All manifests valid"

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
        "ghcr.io/ublue-os/bluefin-dx:latest"
        # Uncomment as variants are added to the matrix:
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

# Pin all tracked image tags to their current SHA256 digest and write images.lock.
# Requires: skopeo on PATH and registry credentials (for ghcr.io, docker login or REGISTRY_AUTH_FILE).
# Usage: just lock-images
lock-images:
    #!/usr/bin/env bash
    set -euo pipefail
    IMAGES=(
        "ghcr.io/ublue-os/bluefin:latest"
        "ghcr.io/ublue-os/bluefin:lts"
        "ghcr.io/ublue-os/bluefin-dx:latest"
        "ghcr.io/ublue-os/bluefin-nvidia:latest"
    )
    LOCKED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    LOCK_FILE="images.lock"
    echo "{" > "${LOCK_FILE}"
    TOTAL=${#IMAGES[@]}
    IDX=0
    for img in "${IMAGES[@]}"; do
        IDX=$((IDX + 1))
        tag="${img##*:}"
        ref="${img%%:*}:${tag}"
        echo "Resolving ${ref}..."
        digest="$(skopeo inspect --format='{{{{.Digest}}}}' "docker://${ref}" 2>/dev/null)"
        if [[ -z "${digest}" ]]; then
            echo "ERROR: could not resolve digest for ${ref}" >&2
            exit 1
        fi
        echo "  ${ref} → ${digest}"
        COMMA=","
        [[ ${IDX} -eq ${TOTAL} ]] && COMMA=""
        printf '  "%s": {"image": "%s", "digest": "%s", "locked_at": "%s"}%s\n' \
            "${tag}" "${ref}" "${digest}" "${LOCKED_AT}" "${COMMA}" >> "${LOCK_FILE}"
    done
    echo "}" >> "${LOCK_FILE}"
    echo "✓ Written ${LOCK_FILE}"
    cat "${LOCK_FILE}"

# ── CI/CD ────────────────────────────────────────────────────────────────────

# Manually re-trigger a test run from the CLI (mirrors GitHub Actions manual.yml).
# Usage: just trigger-pr latest smoke
# Usage: just trigger-pr dx-latest dx ghcr.io/ublue-os/bluefin-dx:latest
trigger-pr tag="latest" suite="smoke" img="":
    #!/usr/bin/env bash
    set -euo pipefail
    : "${BLUEFIN_TEST_PUBKEY:?Run 'just setup-ssh-secret' then 'source .env.test-pubkey'}"
    IMAGE="{{ img }}"
    if [[ -z "${IMAGE}" ]]; then
        case "{{ tag }}" in
            lts)          IMAGE="ghcr.io/ublue-os/bluefin:lts" ;;
            dx-latest)    IMAGE="ghcr.io/ublue-os/bluefin-dx:latest" ;;
            vanilla-gnome) IMAGE="quay.io/fedora/fedora-bootc:latest" ;;
            *)            IMAGE="ghcr.io/ublue-os/bluefin:{{ tag }}" ;;
        esac
    fi
    echo "Submitting: image=${IMAGE} tag={{ tag }} suite={{ suite }}"
    argo submit argo/bluefin-smoke-test.yaml \
        -p image="${IMAGE}" \
        -p image-tag="{{ tag }}" \
        -p suite="{{ suite }}" \
        -p ssh-pubkey="${BLUEFIN_TEST_PUBKEY}" \
        -p pr-title="manual:$(whoami)" \
        -n {{ argo_ns }} \
        --watch

# Print instructions for registering a GitHub Actions self-hosted runner on ghost
setup-runner:
    @echo "=== Register GitHub Actions self-hosted runner on ghost ==="
    @echo ""
    @echo "1. Go to: https://github.com/projectbluefin/testsuite/settings/actions/runners/new"
    @echo "   Select: Linux / x64"
    @echo "   Copy the registration token shown on that page."
    @echo ""
    @echo "2. On ghost, run:"
    @echo "   mkdir -p ~/actions-runner && cd ~/actions-runner"
    @echo "   curl -L https://github.com/actions/runner/releases/latest/download/actions-runner-linux-x64-2.316.1.tar.gz | tar xz"
    @echo "   ./config.sh --url https://github.com/projectbluefin/testsuite --token <TOKEN> --labels ghost --unattended"
    @echo "   sudo ./svc.sh install && sudo ./svc.sh start"
    @echo ""
    @echo "3. Add repository secret BLUEFIN_TEST_PUBKEY:"
    @echo "   gh secret set BLUEFIN_TEST_PUBKEY -R projectbluefin/testsuite"
    @echo "   (paste contents of .env.test-pubkey when prompted)"

# List all stub/future test scenarios not yet implemented
list-stubs:
    #!/usr/bin/env bash
    echo "=== Stubbed scenarios (@future tag) ==="
    grep -r '@future' tests/*/features/*.feature 2>/dev/null | sed 's/.*tests/  tests/' || echo "  (none)"
    echo ""
    echo "=== NotImplementedError stubs ==="
    grep -rn 'raise NotImplementedError' tests/*/features/steps/*.py 2>/dev/null | sed 's/.*tests/  tests/' || echo "  (none)"

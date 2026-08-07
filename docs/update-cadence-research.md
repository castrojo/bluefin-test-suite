# Smarter Update Cadence informed by testsuite validation

> Research & design — issue projectbluefin/testsuite#431.
> Status: **proposal for discussion**. No implementation until a spec is agreed.
> Last updated: 2026-08-07

## TL;DR

1. **Metadata transport**: publish test results as OCI annotations on the image
   (`org.ublue.test.*`), backed by a machine-readable summary file inside the
   image (`/usr/share/ublue/update-metadata.json`). Both are consumable by the
   client at stage time with zero extra network calls.
2. **Gate vs advisory**: two-tier. A **hard gate** blocks *promotion to
   `:stable`* for boot-critical failures (unbootable, login loop, black
   screen). Everything else becomes **advisory metadata** the client's update
   logic weighs (soak, delta size, confidence).
3. **Confidence score**: `min(coverage, soak, delta, telemetry)` style
   composite — a score between 0 and 1 that clients can threshold against.
4. **MVP client change**: read the metadata before staging; skip staging when
   metadata is absent/blocked/boot-failed; fix the timer's wake/resume path
   (network-ready gate, backoff); record boot success after reboot
   (`grub-boot-success`) and feed it back into the next decision.

---

## 1. Problem space

A survey of `ublue-os` issues shows the current mechanism — a fixed-timer
`rpm-ostreed-automatic` that stages the latest `:stable` and reboots — has no
intelligence about *when* to update or *whether* the candidate is safe.

### 1.1 Timer fires when the machine can't update

| Issue | Failure |
| --- | --- |
| ublue-os/uupd#85 | `Persistent=true` fires the missed 4am timer on wake; DNS is not ready yet → `Temporary failure in name resolution`, update fails |
| ublue-os/config#90 | Same DNS-not-ready failure at 4am even on wired networks; manual `rpm-ostree upgrade` succeeds |
| ublue-os/config#89 | Flatpak auto-update timers fire before the D-Bus user session exists |

Current mitigations (network-online target, metered-connection check, 10min
randomized delay) reduce but do not eliminate these races. There is no retry
with backoff and no "was the last attempt a transient failure?" state.

### 1.2 Daily builds with no quality gate ("update roulette")

| Issue | Failure |
| --- | --- |
| ublue-os/bluefin#2157 | `stable-20250126.1` unbootable on Nvidia |
| ublue-os/bluefin#3908 | Black screen after update |
| ublue-os/bluefin#4308 | `systemd-sleep` missing capability → battery drain after update |
| ublue-os/bluefin#4343 | ~120-package delta on Framework AMD: TTY boot, GDM freeze, no WiFi |
| ublue-os/bluefin#4618 | Login loop after 43→44 (low disk space during upgrade) |

The common thread: an image reaches `:stable` and is auto-staged by the fleet
before anyone has booted it successfully. There is no soak period, no
delta-size awareness, and no boot-success feedback loop.

### 1.3 Current mechanism (verified, 2026-08)

**Client (ublue-os/config):**
- `rpm-ostreed-automatic.timer`: `OnCalendar=*-*-* 4:00:00`, `Persistent=true`,
  `RandomizedDelaySec=10m`.
- `rpm-ostreed-automatic.service`: `Wants=network-online.target` +
  `After=network-online.target`, `ExecCondition` skips metered connections,
  then `rpm-ostree upgrade` (stages `:stable`) → uupd reboots.

**Image pipeline (ublue-os/bluefin):**
- `build-image-stable.yml` builds the `stable` stream: `stable-daily` mutable
  tags every build, `:stable` promoted on the Tuesday schedule or
  workflow_dispatch. **The testsuite is not a gate on promotion today.**

**Testsuite (projectbluefin/testsuite + lab):**
- Behave suites: `smoke`, `developer`, `software`, `lifecycle`, `security`,
  `dx`, `nvidia`, `hardware`, `vanilla-gnome`, `flatcar` (162 scenarios).
- Executed against candidate images by the lab pipelines
  (`bluefin-qa-pipeline`, default `image-tag: testing`, suites
  `smoke,common,developer,software,system`) with an evidence contract
  (`bluefin.io/evidence-contract: qa-run-v1`); results are aggregated into a
  results dashboard.

So the machinery to *know* whether an image is good exists; it is just not
wired into either the promotion decision or the client's staging decision.

---

## 2. Q1 — What metadata can the testsuite publish for clients?

### 2.1 Options

| Option | Transport | Pros | Cons |
| --- | --- | --- | --- |
| **A. OCI annotations** | `org.ublue.test.*` labels on the image config | Zero extra network; readable with `skopeo inspect` / bootc metadata before staging | Annotation size limits (64KB total); annotations are not signed by default |
| **B. Metadata file in image** | `/usr/share/ublue/update-metadata.json` | Arbitrary size; versionable; readable offline once staged | Requires inspecting/pulling the image first (defeats "check before staging" unless registry blob read is used) |
| **C. Signed attestation** | in-toto/SLSA attestation pushed to the registry alongside the image (cosign) | Tamper-evident; cryptographically binds test results to the digest | More moving parts; clients need cosign verification at stage time |
| **D. Sidecar service** | HTTP API (e.g., `results.projectbluefin.io`) | No image coupling; rich queries | Requires network at decision time; another service to operate; bootc staging path has no hook for it |

### 2.2 Recommendation

**Primary: A (OCI annotations) + B (embedded JSON summary).** The CI pipeline
already knows the test verdict when it tags an image, so it can stamp
annotations at build/tag time. The embedded JSON gives clients a richer,
versioned payload once the image is (or is being) fetched.

**Suggested annotation namespace** (mirrors `org.opencontainers.image.*`):

```text
org.ublue.test.status           = passed | failed | blocked | untested
org.ublue.test.quality          = gold | silver | bronze | untested   (confidence tier)
org.ublue.test.suites           = "smoke developer software lifecycle system"
org.ublue.test.suites-passed    = "smoke developer software lifecycle"
org.ublue.test.suites-failed    = "system"
org.ublue.test.delta-packages   = "120"
org.ublue.test.soak-hours       = "48"        (0 on first publish)
org.ublue.test.validated-at     = "2026-08-07T04:00:00Z"
org.ublue.test.evidence-contract= "qa-run-v1" (link to the contract that produced it)
```

And the embedded file:

```json
// /usr/share/ublue/update-metadata.json
{
  "schema": 1,
  "image": { "digest": "sha256:…", "tags": ["stable-daily", "stable"] },
  "testsuite": {
    "status": "passed",
    "confidence": 0.82,
    "suites": { "smoke": "passed", "lifecycle": "passed", "nvidia": "blocked" },
    "evidence": "https://results.projectbluefin.io/runs/2026-08-07/bluefin/…",
    "contract": "qa-run-v1"
  },
  "delta": { "packages": 120, "layers-mb": 412 },
  "soak": { "hours": 48, "yanked": false },
  "promoted_at": "2026-08-09T01:00:00Z"
}
```

**Signing (option C) is a later phase**: for the MVP, annotations + JSON are
sufficient; cosign attestation can be layered on when keyless signing is
enabled (the pipeline already supports cosign for provenance).

---

## 3. Q2 — Hard gate or advisory metadata?

### 3.1 Analysis

- **Hard gate on promotion** (testsuite must pass before `main → stable`):
  - Prevents repeat of #2157/#3908/#4343 (image never reaches `stable` if
    smoke fails).
  - Cost: promotion latency. Security hotfixes would wait for a test run
    (currently the suites take on the order of an hour).
  - Risk: testsuite false negatives (an untested hardware path, e.g. Nvidia
    without GPU passthrough) become *silent* production failures — exactly what
    happened with #2157.
- **Pure advisory** (metadata only, client decides):
  - Zero promotion latency; the fleet self-selects based on confidence.
  - Risk: defaults matter. If the client's default is "update whenever
    available", nothing improves.

### 3.2 Recommendation: two-tier

1. **Hard gate — boot-critical, low-false-negative tests only.** Block
   promotion when a *minimal* suite fails: smoke (GNOME boots to a usable
   session), plus lifecycle upgrade/rollback on at least one golden
   configuration. These suites have near-zero false negatives for the failure
   classes in §1.2. The gate lives in the release pipeline (lab), not on the
   client.
2. **Advisory metadata — everything else.** Coverage breadth, soak, delta
   size, confidence, and any hardware-specific caveats (e.g., "nvidia:
   untested") go to the client as annotations/JSON. The client uses them to
   decide *when* and *how* to stage.

This keeps security hotfixes fast (advisory metadata can mark a hotfix
"promote-now, skip soak") while making the common case safe.

> Open question for consensus: is a hard gate on `:stable` acceptable to
> maintainers, given it adds 30–90min to the promotion path and needs a
> fallback for emergency unblocking (e.g., `workflow_dispatch` bypass with a
> documented, audited reason)?

---

## 4. Q3 — Confidence score

A single number clients can threshold on. Proposal:

```
confidence = min(coverage, soak, delta, telemetry)
```

Each component in `[0, 1]`:

| Component | Definition | Example |
| --- | --- | --- |
| `coverage` | Weighted fraction of relevant suites passed. Weights reflect how predictive a suite is for the client's hardware class (smoke highest; nvidia only counts for nvidia clients). | smoke 1.0, lifecycle 1.0, nvidia untested → 0.75 on nvidia hardware, 1.0 on generic |
| `soak` | `min(1, hours_as_stable / TARGET_SOAK)` where `TARGET_SOAK` ≈ 48h; 0 if the image was yanked at any point (see §5). | 48h → 1.0; 6h → 0.125; yanked → 0 |
| `delta` | `1 - min(1, delta_packages / DELTA_BUDGET)` with `DELTA_BUDGET` ≈ 100 packages (or layer-MB equivalent). Large deltas lower confidence. | 15 pkgs → 1.0; 120 pkgs → 0.0 |
| `telemetry` | Fraction of fleet boots that reported `grub-boot-success` since promotion; 0 until enough samples exist. | 50/50 good → 1.0; 3/20 → 0.15; unknown → 0 |

**Tiers** (for human-readable labels and defaults):

| Tier | Score | Client default behavior |
| --- | --- | --- |
| `gold` | ≥ 0.85 | Auto-stage on schedule |
| `silver` | 0.5 – 0.85 | Auto-stage, but hold reboot until idle / user confirms |
| `bronze` | 0.25 – 0.5 | Do not stage automatically; show in `ujust update` as available |
| `blocked` | < 0.25 or `status=failed` | Never stage; suppress from the normal update flow |

**Why `min`**: any single red flag (huge delta, no soak, failed suite) should
override otherwise-good scores — a mean would let a great coverage score mask a
120-package delta (#4343).

> Open question: who owns the scoring implementation? Proposal: testsuite
> produces the raw facts (annotations); the client (uupd or a small
> `ublue-update-cadence` helper) computes the score from them. This keeps the
> client self-contained and lets scoring policy evolve without image rebuilds.

---

## 5. Q4 — Minimum viable client-side change

Goal: stop staging known-bad or untested images with the least code. Order of
increasing cost:

1. **Read metadata before staging** (annotation via `skopeo inspect` on the
   staged ref, or the embedded JSON after fetch):
   - `status=failed|blocked` → skip staging entirely (log + fall back to
     `ujust update`).
   - missing metadata → treat as `untested` and *do not auto-stage* (this is
     the key behavioral change; see note).
2. **Fix the wake/resume timer path** (uupd#85, config#90):
   - keep `Persistent=true` but add a **network-ready gate with retry/backoff**
     (e.g., `NetworkManager-wait-online` is insufficient on resume; use a
     `busctl`-checked NM state + `getent hosts ghcr.io` retry loop, 3 attempts,
     exponential backoff, then defer to next timer instead of failing).
   - defer with `systemctl restart rpm-ostreed-automatic.timer`-style reschedule
     rather than hard failure on transient errors.
3. **Boot-success feedback loop**:
   - `grub-boot-success` already runs 2 minutes after a successful session.
   - Have the update service write a marker (`/var/lib/ublue/last-update-ok`)
     on boot success, and clear it pre-reboot; on next scheduled run, if the
     marker is missing **and** a new image is available, rank the candidate
     down (or skip) until a human intervenes (#4618-style login loops self-limit
     instead of repeating).
   - Report the marker (anonymized) to the telemetry component of the
     confidence score.
4. **Respect soak/delta tiers from §4** — the cheapest version is a static
   table (`stable` promoted < 24h ago → wait for next window); the full version
   consumes the annotations.

### 5.1 "Untested = don't auto-stage" is the crux

The single highest-leverage change: **the client should not auto-stage an
image that has no test evidence at all.** Today every daily build is
auto-staged by the fleet within 24h; adding "no evidence → hold, show in
`ujust update`" turns the testsuite from a nice-to-have into a genuine safety
net with a one-line default in the update policy. This is deliberately
conservative and can be relaxed per-image by publishing `status=passed`.

> Open question: how aggressive should the default be? Options: (a) hold
> auto-stage until `status=passed` evidence exists (safe, may delay first
> update of the day by the test-run window); (b) auto-stage `untested` but with
> `bronze` tier behavior (no auto-reboot). Recommend (b) for the MVP to avoid
> a new failure mode (people never updating), with (a) as a documented
> hardening toggle.

---

## 6. Proposed architecture

```text
                        ┌─────────────────────────────┐
                        │  bluefin build pipeline     │
                        │  build-image-stable.yml     │
                        └──────────────┬──────────────┘
                                       │ image (stable-daily)
                                       v
                        ┌─────────────────────────────┐
                        │  lab QA pipeline            │  ← testsuite content
                        │  bluefin-qa-pipeline        │
                        │  (smoke, lifecycle, ...)    │
                        └──────────────┬──────────────┘
                                       │ results (pass/fail per suite)
                                       v
              ┌────────────────────────┴────────────────────────┐
              │  Promotion gate (hard: smoke+lifecycle)         │
              │  + metadata stamping (annotations + JSON)       │
              └────────────────────────┬────────────────────────┘
                                       │ :stable (+ org.ublue.test.*)
                                       v
                        ┌─────────────────────────────┐
                        │  Registry (GHCR)            │
                        │  image + annotations + JSON │
                        └──────────────┬──────────────┘
                                       │
              ┌────────────────────────┴────────────────────────┐
              │  Client (rpm-ostreed-automatic / uupd)          │
              │  1. read metadata       3. boot-success marker  │
              │  2. tier decision       4. backoff/reschedule   │
              └─────────────────────────────────────────────────┘
```

**Ownership split (respects the repo boundary):**
- testsuite: defines the evidence contract and the metadata schema (this doc
  becomes the contract reference).
- lab: runs the pipeline, enforces the hard gate, stamps annotations.
- ublue-os/config / uupd: consumes metadata, implements client heuristics.

---

## 7. Phased roadmap

| Phase | Scope | Where |
| --- | --- | --- |
| **0. Contract** (this issue) | Agree schema, gate tier, scoring, defaults | testsuite docs |
| **1. Evidence** | Pipeline stamps `org.ublue.test.status` + JSON from existing runs; results dashboard links in evidence URL | lab |
| **2. Hard gate** | Smoke+lifecycle gate on `:stable` promotion with documented bypass | lab |
| **3. Client MVP** | Read metadata; "untested → bronze"; wake/resume backoff; boot-success marker | config / uupd |
| **4. Scoring** | Full confidence score + telemetry aggregation; soak/delta tiers | config / uupd + lab |
| **5. Attestation** | Cosign-signed test attestations; client verification | all |

---

## 8. Open questions for consensus

1. Is a hard gate on `:stable` promotion acceptable (adds 30–90min, needs an
   audited bypass)? Or should the gate only mark metadata and let clients
   decide?
2. Default client posture for `untested` images: hold auto-stage entirely, or
   auto-stage without auto-reboot (§5.1)?
3. Who owns the confidence-score computation — client-side (recommended) or
   server-side in the metadata?
4. Soak target: 24h, 48h, or tied to the Tuesday `:stable` cadence?
5. Is the `org.ublue.test.*` annotation namespace acceptable, and should the
   JSON schema live in this repo as a versioned file
   (`docs/schemas/update-metadata.schema.json`)?

---

## 9. References

- ublue-os/uupd#85 — update fails on wake from suspend
- ublue-os/config#89 — flatpak timers before D-Bus session
- ublue-os/config#90 — rpm-ostree update fails (DNS not ready)
- ublue-os/bluefin#2157 — stable unbootable on Nvidia
- ublue-os/bluefin#3908 — black screen after update
- ublue-os/bluefin#4308 — battery drain after update
- ublue-os/bluefin#4343 — instability after ~120-package delta
- ublue-os/bluefin#4618 — login loop (low disk space)
- projectbluefin/testsuite — behave suite map (QA-REVIEW.md)
- projectbluefin/lab — `bluefin-qa-pipeline`, result aggregation
- ublue-os/bluefin — `build-image-stable.yml` (stable stream / Tuesday promotion)
- ublue-os/config — `rpm-ostreed-automatic.{timer,service}` overrides

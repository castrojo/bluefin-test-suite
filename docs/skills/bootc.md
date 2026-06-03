# bootc Lifecycle Testing Reference

Load when: writing or debugging lifecycle, upgrade, or rollback tests.

## bootc status JSON schema (v1alpha1)

```
bootc status --format=json
```

| Field | Path |
|---|---|
| Active deployment | `.status.booted` |
| Pending reboot | `.status.staged` (null if none) |
| Active image digest | `.status.booted.image.imageDigest` |
| Active image ref string | `.status.booted.image.image.image` |
| Pinned (won't auto-prune) | `.status.booted.pinned` (bool) |

**Wrong paths that cause silent test skips:**
- `.staged` (missing `.status` prefix)
- `.active.imageDigest`
- `.active.image`

Always validate the outer structure before accessing:
```python
payload = json.loads(output)
assert isinstance(payload.get("status"), dict), "bootc status JSON malformed"
booted = payload["status"]["booted"]
```

Bare `payload.get("status", {})` silently accepts malformed JSON — don't use it as a guard.

## Lifecycle capture pattern

Capture digests at the right moments or verification steps silently skip:

```python
# 1. Before upgrade — save current digest
original_digest = get_booted_digest(context)

# 2. Trigger upgrade (bootc upgrade / image swap)

# 3. After upgrade, BEFORE reboot — capture staged digest
expected_upgrade_digest = get_staged_digest(context)

# 4. Reboot VM

# 5. After reboot — assert booted == expected_upgrade_digest
```

Without step 3, the post-reboot assertion has nothing to compare against and silently passes or skips.

## ostree admin status parsing

```
* <ref>    ← active/booted deployment (exactly one)
  <ref>    ← previous deployments (2-space indent, no leading *)
```

Counting `* ` lines gives 1, never 2. To count **all** deployment headers:
```python
import re
count = len(re.findall(
    r'^(?:\* |\s{2}(?!\s))(?=[a-zA-Z0-9])',
    output,
    re.MULTILINE
))
assert count >= 2  # not == 2; multiple upgrades can produce more
```

Assert `>= 2`, not `== 2` — after multiple upgrades there can be more than two deployment entries.

## Cross-registry migration (ublue-os → projectbluefin)

`tests/lifecycle/features/migration.feature` covers the user journey of migrating from the legacy `ghcr.io/ublue-os/bluefin` image (built with rpm-ostree / `ublue-os/legacy-rechunker`) to `ghcr.io/projectbluefin/bluefin` (built with chunkah OCI format).

### Invoking migration tests

```yaml
uses: projectbluefin/actions/.github/workflows/upgrade-test.yml@v1
with:
  image: ghcr.io/ublue-os/bluefin:latest   # start on the legacy source
  suites: lifecycle
```

The VM must start on the `ublue-os` registry image — every scenario has a registry guard step that fails fast if the wrong starting image is used.

### 6 scenarios, 2 storage lanes

| Scenario tags | Storage mode | Key assertion |
|---|---|---|
| `@switch` | standard bootc | Active ref contains `projectbluefin/bluefin`; digest matches staged |
| `@switch @rollback` | standard bootc | Rollback returns to original `ublue-os` digest |
| `@switch @health` | standard bootc | `booted.incompatible` absent; `/etc/os-release` reports Bluefin |
| `@switch @unified_storage` | `--experimental-unified-storage` | `/var/lib/bootc/storage/overlay` present post-reboot |
| `@switch @unified_storage @rollback` | `--experimental-unified-storage` | Rollback digest matches original `ublue-os` deployment |
| `@chunkah` | standard bootc | `.status.rollback.image.imageDigest` == original source digest |

### Parameterized target and timeouts

Migration steps use `MIGRATION_TARGET` env var (default: `ghcr.io/projectbluefin/bluefin:stable`):

```
* Switch to migration target                        # 900s timeout — image pull takes 5-15 min
* Switch to migration target with unified storage   # 900s + --experimental-unified-storage
* Check unified storage support and skip if unavailable  # graceful skip on bootc < 1.16
* Reboot VM and wait for SSH after migration        # 300s deadline (rechunker-group-fix first-boot)
```

Do NOT use `Run SSH command: "sudo bootc switch ..."` for migration — the default 60s SSH timeout will fire before the pull completes.

### Key step: rollback uses digest, not ref string

```python
# CORRECT: digest is the reliable identity after bootc rollback
active_digest = status["booted"]["image"]["imageDigest"]
assert active_digest == context.original_digest

# WRONG: exact ref string may differ after rollback reordering
assert "ublue-os" in active_ref  # informational only, not the assertion
```

### bootc status JSON path for rollback

```
.status.rollback.image.imageDigest   — SHA256 of the preserved deployment
.status.rollback.image.image.image   — image ref string
```

After `bootc switch` + reboot, `.status.rollback` contains the pre-migration deployment. After `bootc rollback` + reboot, `.status.rollback` contains the post-migration deployment. Both are non-null as long as two deployments are present.

### Unified storage overlay path

After `bootc switch --experimental-unified-storage` + reboot:
```
/var/lib/bootc/storage/overlay   — containers-storage backing dir (must exist)
```
Standard bootc storage does NOT create this path. The testsuite asserts its presence to distinguish the two storage modes.



`sudo bootc pin` sets `.status.booted.pinned = true` — the deployment is protected from auto-pruning.  
`sudo bootc pin --unpin` clears it.

Step definitions in `tests/lifecycle/features/steps/steps.py`:
```
* bootc status shows deployment is pinned
* bootc status shows deployment is not pinned
```

Both use `_parse_bootc_status(context)` for validated JSON access — do not duplicate the bare `json.loads` pattern.


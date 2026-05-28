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

## bootc pin / unpin

`sudo bootc pin` sets `.status.booted.pinned = true` — the deployment is protected from auto-pruning.  
`sudo bootc pin --unpin` clears it.

Step definitions in `tests/lifecycle/features/steps/steps.py`:
```
* bootc status shows deployment is pinned
* bootc status shows deployment is not pinned
```

Both use `_parse_bootc_status(context)` for validated JSON access — do not duplicate the bare `json.loads` pattern.

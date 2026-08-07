---
name: bootc
description: "How to write bootc upgrade, rollback, and migration tests for the testsuite repo. Load when editing bootc-related .feature files or steps."
metadata:
  type: pattern
  audience: agents
  maturity: stable
---

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


## Flatcar: verifying Ignition ran

Ignition executes **in the initramfs**, so its systemd units (`ignition-*.service`,
`ignition-complete.target`) are not visible from the booted root. Do not assert on
`systemctl status ignition-*` — those checks pass vacuously.

The observable proof of a successful run is the ESP first-boot marker. GRUB sets
`flatcar.first_boot=detected` when `flatcar/first_boot` exists on the EFI System
Partition, and Ignition deletes that file only after it completes successfully:

```gherkin
* Flatcar ESP is mounted at /boot
* Ignition first-boot marker is cleared
* Ignition-provisioned SSH keys are present for the test user
```

**Always assert the ESP is mounted first.** `/boot/flatcar/first_boot` is checked for
*absence*; if `/boot` were not mounted the absence check would pass trivially. The
`Flatcar ESP is mounted at /boot` step asserts `findmnt -no FSTYPE /boot` reports
`vfat`, which closes that false-pass hole.

SSH-key placement differs by image age — Ignition writes either
`~/.ssh/authorized_keys` or an `~/.ssh/authorized_keys.d/` fragment (the
`update-ssh-keys` layout). Accept both and assert on the return code; never parse
the key file's contents.

### Never infer "file absent" from a nonzero SSH return code

`run_ssh(context, "test -e /boot/flatcar/first_boot")` returning nonzero does **not**
mean the marker is gone: rc 255 is an SSH transport failure, so an unreachable VM
produces a green Ignition check. Use a probe that exits 0 whenever the connection
worked and reports the answer in stdout:

```python
run_ssh(context, f"test -e {FIRST_BOOT_MARKER} && echo present || echo absent")
ssh_return_code_is(context, "0")          # transport failure fails here
state = context.command_stdout.strip()
assert state in {"present", "absent"}      # unexpected output is a failure too
assert state == "absent"
```

### A cleared marker alone does not prove *your* config was applied

The first-boot marker and "the user has some SSH key" are both satisfied by an empty
Ignition config plus externally provisioned keys. To claim real Ignition coverage,
assert on an artifact the suite's *own* Ignition config uniquely provisions (a
suite-owned file, hostname, or systemd unit). Until such an artifact exists, tag the
scenario `@pending` with a named blocker rather than advertising the weaker check as
coverage.

## Flatcar: disabling automatic updates

There is **no `update_strategy` setting in Flatcar.** The two real knobs both live in
`/etc/flatcar/update.conf`:

| Key | Effect |
|---|---|
| `SERVER=disabled` | Disables automatic updates (upstream's recommended switch; what `flatcar-update --disable-afterwards` writes) |
| `REBOOT_STRATEGY=off` | Update is still downloaded to the passive partition; only the *reboot* is suppressed |

Upstream explicitly discourages masking `update-engine.service` / `locksmithd.service`,
because a masked `update-engine` cannot mark a freshly booted partition successful and
GRUB then rolls back. So `systemctl is-active update-engine` is **not** a valid
"updates are disabled" assertion — after disabling, the unit must still be `active`.

Parse `update.conf` with `parse_update_conf()` / `automatic_updates_disabled()` in
`tests/flatcar/features/steps/steps.py` rather than grepping. It is a shell-sourced
`KEY=VALUE` fragment: values may be quoted, `#` comments are ignored, and later
assignments win.

Any scenario that mutates `update.conf` must back it up first and restore it in both
an explicit final step *and* `after_scenario`, so a mid-scenario failure cannot leave
the VM with updates permanently off.

**Clear the "backed up" flag only after restoration is verified.** Clearing it before
the assertions turns the `after_scenario` hook into a no-op on a failed restore, so
the VM keeps automatic updates disabled for the rest of the run with no retry:

```python
run_ssh(context, f"sudo test -e {BACKUP} && sudo mv -f {BACKUP} {UPDATE_CONF} && ...")
ssh_return_code_is(context, "0")
run_ssh(context, f"cat {UPDATE_CONF}")
ssh_return_code_is(context, "0")
assert not automatic_updates_disabled(context.command_stdout)
context.update_conf_backed_up = False     # last, never first
```

## Flatcar: what still needs the lab

The flatcar suite is not referenced anywhere in `.github/workflows/e2e.yml`, so no
flatcar scenario can run in CI today (tracked in #704). Scenarios written against it
stay `@pending` with a named blocker comment until the suite is wired up — an
"active" scenario that can never execute misreports coverage.

Booting the disk that `knuckle` just installed to requires swapping the KubeVirt VM's
boot device. That lives in the VM spec, owned by `projectbluefin/lab`, not this repo.
Without it a reboot silently returns to the live rootdisk and the scenario passes while
testing nothing — which is why that scenario stays `@future` rather than being written
optimistically.

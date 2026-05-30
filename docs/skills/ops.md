# Operational Gotchas

Load when: a VM boots to GDM greeter, a workflow is stuck Pending, or you're debugging infra-layer failures.

These are testsuite-affecting infra issues. Root fixes belong in `projectbluefin/testing-lab`; this doc records the symptoms and workarounds agents need mid-task.

## GDM autologin required

**Symptom:** VM boots but all scenarios fail in `before_scenario` with `gnome-ponytail-daemon` D-Bus name not activatable. Zero tests run.

**Cause:** `bib-disk-configure` did not write GDM autologin config. VM boots to GDM greeter — no graphical session starts, so `gnome-ponytail-daemon` cannot activate.

**Required config** (must be on the golden disk image):
```ini
# /etc/gdm/custom.conf
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=bluefin-test
```

**Fix:** Open an issue in `projectbluefin/testing-lab` referencing the `bib-disk-configure` step. Do not add this workaround to testsuite step code.

Tracked: testsuite issue #33.

## Zombie Argo mutex

**Symptom:** A workflow is stuck `Pending` indefinitely. `exo-1` is down or not scheduling pods. `ResourcesDuration` is near zero. The workflow holds a mutex and blocks all subsequent workflows.

**Detect:**
```bash
argo list -n argo --status Running
argo get <workflow-name> -n argo | grep -E "Status|Node|Duration"
```

**Fix:**
```bash
argo stop <workflow-name> -n argo
```

This releases the mutex. **Do not** delete the workflow — `stop` preserves the audit trail.

> This applies only to the legacy Argo stack in `projectbluefin/testing-lab`. SSH-mode suites (lifecycle, security, hardware) still use it until the GHA SSH-mode action is built (epics #43/#44).

## SSH step timeout tuning

Default `run_ssh()` timeout is **60 seconds**, not 30. Hardware commands (bootc upgrade, disk ops, systemctl restart) are slow in emulated VMs. If a step times out at 30s, check the `timeout=` kwarg in `tests/shared/ssh_steps.py` — you can override it per-call:

```python
run_ssh(context, "sudo bootc upgrade", timeout=180)
```

Never lower the default below 60s.

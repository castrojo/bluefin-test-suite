---
name: smoke-vs-ssh
description: "When to use local subprocess instead of SSH in the smoke suite."
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## Smoke suite — local subprocess (not SSH)

The smoke suite runs **inside** the VM via qecore-headless. Steps in `tests/smoke/features/steps/` execute locally using `subprocess.run`, **not** over SSH.

```python
def _run(cmd: str):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout.strip(), result.returncode, result.stderr.strip()
```

**Never** import `tests.shared.ssh_steps` into the smoke environment — those steps require `context.vm_ip` / `context.ssh_key` which don't exist in the smoke context, and will collide with qecore step phrases.

For system-level checks in `system_health.feature`, define named steps in `system_health_steps.py` that call `_run()` directly. For tools that reside on the VM host and not in the runner container (such as tailscale, uupd, and fastfetch), define custom steps that call `_run_host()` to run them on the host VM via SSH.

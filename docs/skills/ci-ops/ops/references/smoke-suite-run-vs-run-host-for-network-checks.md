---
name: smoke-suite-run-vs-run-host-for-network-checks
description: "Deep dive: Smoke suite: _run() vs _run_host() for network checks"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Smoke Suite Run Vs Run Host For Network Checks

## Smoke suite: _run() vs _run_host() for network checks

**Symptom:** DNS health check in `system_health.feature` passes even when the VM has no connectivity.

**Cause:** `_run(cmd)` in the smoke suite executes on the test runner (inside the VM-side container), NOT in the actual VM guest OS. For network or system checks that need to reflect the VM's actual state, use `_run_host(cmd)` which executes in the VM via a shell bridge.

```python
_run("getent hosts ghcr.io")

_run_host("getent hosts ghcr.io")
```

Use `_run_host()` for: DNS lookups, network connectivity, firewall state, systemd service status from the host OS.
Use `_run()` for: subprocess calls within the test runner environment (extension state via gdbus, GNOME shell interactions).

---

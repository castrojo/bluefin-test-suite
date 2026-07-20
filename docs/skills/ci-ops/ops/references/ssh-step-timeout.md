---
name: ssh-step-timeout
description: "Deep dive: SSH step timeout"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Ssh Step Timeout

## SSH step timeout

Default `run_ssh()` timeout is **60 seconds**, not 30. Hardware commands (bootc upgrade, disk ops) are slow in emulated VMs.

```python
run_ssh(context, "sudo bootc upgrade", timeout=180)
```

Never lower the default below 60s.

---

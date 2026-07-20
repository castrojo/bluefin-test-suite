---
name: python-3-14-sys-executable-is-empty-in-pid-host-containers
description: "Deep dive: Python 3.14: sys.executable is empty in --pid=host containers"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Python 3 14 Sys Executable Is Empty In Pid Host Containers

## Python 3.14: sys.executable is empty in --pid=host containers

**Symptom:** All scenarios fail with `PermissionError: [Errno 13] Permission denied: ''` in `behave_retry.py`.

**Cause:** Python 3.14 sets `sys.executable = ''` inside podman `--pid=host` containers.

**Fix:** `_find_python()` in `behave_retry.py` probes `sys.executable`, then `shutil.which("python3")`, then known absolute paths. Never use `sys.executable` directly for subprocess invocation.

---

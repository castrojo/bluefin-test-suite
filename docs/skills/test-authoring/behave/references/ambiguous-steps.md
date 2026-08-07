---
name: ambiguous-steps
description: "Avoiding duplicate step phrases and AmbiguousStep errors."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Ambiguous Steps

## Avoiding AmbiguousStep with qecore.common_steps

`from qecore.common_steps import *` registers qecore's steps in behave's global registry on first import. If your `steps.py` defines the **same pattern string** you get `AmbiguousStep` at runtime (not import time).

Fix: give suite-local steps a distinct phrase.
```python
# BAD — collides with qecore
@step("Run and save command output:")

# GOOD — unique to this suite
@step("Run DX SSH command:")
```

Check for collisions before committing:
```bash
grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d
```

All step files under a suite directory are loaded together — duplicates across files in the same suite are also ambiguous.

## Collisions with tests/shared/ssh_steps.py

Star-importing `tests/shared/ssh_steps` registers **all** of its phrases —
including `No coredump entries exist for "{name}"`, which runs `coredumpctl`
**locally** (correct for suites where behave executes on the test VM). Suites
that run behave in a runner container and SSH to the VM (e.g. smoke, via
`_run_host`) must keep their own host-checking step under a **distinct**
phrase — smoke uses `No coredump entries exist on the host for "{name}"`.
Deleting the suite-local step instead would silently point existing scenarios
at the wrong target (runner container, not the VM).

Importing *any* name from `ssh_steps` executes the whole module and registers
every phrase, so selective imports do **not** avoid the collision — rename the
suite-local phrase instead.

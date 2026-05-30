# Behave Patterns Reference

Load when: writing behave tests, scaffolding new suites, or debugging step resolution errors.  
Hard rules live in `docs/skills/index.md` — this doc holds patterns and examples only.

## Shared SSH helpers

`tests/shared/ssh_steps.py` is canonical for:
- `Bluefin VM is booted and reachable over SSH`
- `Run SSH command`
- `SSH command return code is`

Import in suite `environment.py`:
```python
from tests.shared.ssh_steps import *  # noqa: F401,F403
```

Never duplicate `_ssh()` or generic step definitions in suite-specific `steps.py`.  
Default `run_ssh()` timeout: **60s** (not 30s — hardware commands are slow).

## Smoke suite — local subprocess (not SSH)

The smoke suite runs **inside** the VM via qecore-headless. Steps in `tests/smoke/features/steps/` execute locally using `subprocess.run`, **not** over SSH.

```python
def _run(cmd: str):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout.strip(), result.returncode, result.stderr.strip()
```

**Never** import `tests.shared.ssh_steps` into the smoke environment — those steps require `context.vm_ip` / `context.ssh_key` which don't exist in the smoke context, and will collide with qecore step phrases.

For system-level checks in `system_health.feature`, define named steps in `system_health_steps.py` that call `_run()` directly.

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

## Feature scaffolding with @future

Use `@future` when the VM spec, Argo template, or step implementation isn't ready yet:

```gherkin
@future
Scenario: Hardware watchdog is active
    Given the VM has TPM 2.0
    ...
```

Remove `@future` when all three are true:
1. VM spec supports the hardware/feature
2. Argo template wires the suite
3. Step implementations are complete

Find remaining stubs:
```bash
grep -r "@future" tests/*/features/*.feature
# or
just list-stubs
```

## Suite layout

```
tests/
  smoke/          # GUI smoke — behave + dogtail
  developer/      # developer tools
  software/       # software installation
  flatcar/        # Flatcar compatibility
  lifecycle/      # bootc upgrade/rollback
  security/       # security posture
  dx/             # DX variant
  nvidia/         # GPU tests
  hardware/       # hardware feature detection
  vanilla-gnome/  # upstream GNOME parity
  shared/
    ssh_steps.py  # canonical SSH step library
```

Each suite has:
```
<suite>/
  features/
    *.feature
    environment.py
    steps/
      steps.py   (+ additional step files)
```

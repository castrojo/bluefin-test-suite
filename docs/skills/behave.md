---
name: behave-patterns
description: "Behave test patterns for projectbluefin/testsuite — step structure, shared SSH helpers, suite scaffolding, and debugging step resolution errors."
metadata:
  type: reference
---

# Behave Patterns Reference

Load when: writing behave tests, scaffolding new suites, or debugging step resolution errors.

## When to Use

- Adding or refactoring behave feature files and step definitions
- Debugging undefined or ambiguous steps
- Verifying local validation commands before pushing a PR

## When NOT to Use

- GNOME Shell / AT-SPI behaviour questions specific to desktop automation — use `docs/skills/gnome.md`
- VM / runner infrastructure failures — use `docs/skills/ops.md`
- Suite selection, coverage counts, or gap tracking — use `docs/skills/suite-map.md`

## Core Process

1. Pick the correct suite and keep feature files plus step files in sync.
2. Reuse the canonical helper for the suite context (shared SSH helpers or smoke local subprocess).
3. Check for duplicate step phrases before committing.
4. Run `behave --dry-run` to catch undefined or ambiguous steps before pushing.
5. Update related docs and counts when scenario coverage changes.


## Shared SSH helpers

`tests/shared/ssh_steps.py` is canonical for:
- `Bluefin VM is booted and reachable over SSH`
- `Run SSH command: "<cmd>"`
- `SSH command return code is "<code>"`
- `SSH command output "is" "<expected>"`
- `SSH command output stripped "is" "<expected>"`
- `SSH command output contains "<text>"`
- `SSH command output does not contain "<text>"`
- `SSH command output is not "<value>"`
- `SSH command output is not "<a>" and not "<b>"`
- `SSH command output is not empty`

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

## MIME type handler verification (smoke suite)

Use `xdg-mime query default <mime-type>` to verify handler registration without launching apps. Assert against known `.desktop` file names or an allow-set:

```python
DOCUMENT_VIEWERS = {"org.gnome.Papers.desktop", "evince.desktop"}
actual = subprocess.run(["xdg-mime", "query", "default", "application/pdf"],
                        capture_output=True, text=True).stdout.strip()
assert actual in DOCUMENT_VIEWERS
```

This validates the MIME database end-to-end (xdg-mime, .desktop file registration, mimeapps.list) without window management flake.

For lightweight smoke-suite CLI assertions (for example `gsettings`, `pgrep`, or `journalctl` checks), prefer qecore's built-in command capture steps in the `.feature` file instead of adding wrappers:

```gherkin
* Run and save command output: "gsettings get org.gnome.desktop.a11y.keyboard enable"
* Return code of last command output "is" "0"
* Last command output "contains" "true"
```

Do **not** invent alternate phrases like `Run command:` / `Command output contains ...` in smoke features unless you are also intentionally adding matching step definitions.

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

For per-image GNOME extension coverage, keep suite-local phrases distinct even when the helper logic is identical. Example: bazzite uses `Extension "{uuid}" is enabled`, while smoke uses `GNOME extension "{uuid}" is enabled` in `tests/smoke/features/steps/steps.py` so new per-UUID Bluefin scenarios can coexist without colliding with existing generic extension steps.

## Feature scaffolding with @future

Use `@future` when the step implementation isn't ready yet:

```gherkin
@future
Scenario: Hardware watchdog is active
    Given the VM has TPM 2.0
    ...
```

Remove `@future` when all three are true:
1. VM spec supports the hardware/feature
2. Step implementations are complete

Find remaining stubs:
```bash
just list-stubs
# or
grep -r "@future" tests/*/features/*.feature
```

## Selective reruns with @retry

Use a plain `@retry` tag on scenarios whose common failure mode is
infrastructure timing (GNOME session startup, AT-SPI render races, slow app
launch in QEMU). `tests/shared/behave_retry.py` only re-runs failing rerun
entries whose effective tags include `retry`; untagged failures fail the job
immediately after the first pass.

The retry budget comes from `BEHAVE_RETRIES` / `--retries` (default: `2`), so
`@retry` means "eligible for the normal retry loop" rather than a per-scenario
count override.

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


## Cross-suite step isolation

Each suite loads only its own `steps/*.py` files plus `qecore.common_steps`. A step defined in `tests/software/features/steps/steps.py` is **not** available in `tests/developer/features/steps/steps.py` even if both import qecore.

**Rule:** When the audit agent (or any agent) moves a step phrase from a shared/smoke context into a suite-specific file, verify that every `.feature` file using that phrase is in the same suite. If multiple suites use the phrase, define it in each suite's `steps.py`.

Lesson surfaced 2026-05-30: `No journal entries match "{pattern}"` was added to `software/steps.py` but `ptyxis.feature` (developer suite) also used it — causing `UndefinedStep` at runtime.

## behave rerun output can contain non-path noise

`behave --format rerun` on 1.3.x adds header comments like:

```text
# -- RERUN: 7 failing scenarios during last test run.
tests/smoke/features/foo.feature:5
```

`tests/shared/behave_retry.py` must filter out comment or non-`.feature[:line]`
entries before retrying. Passing those lines back to behave causes:

```text
ConfigError: No steps directory in '/.../# -- RERUN: 7 failing scenarios ...'
```

## `Last command output stripped "is"` vs multiline output

`stripped "is" "<value>"` strips whitespace from the **entire** captured output and checks equality. This only works correctly for **single-line** command output (e.g. `grep -c`, `echo X`).

For commands that produce multiline output (e.g. `flatpak install ... 2>&1; echo rc:$?`), use `Last command output contains "rc:0"` instead.

```gherkin
# WRONG — fails when flatpak install produces install progress lines
* Last command output stripped "is" "rc:0"

# CORRECT — substring check works with multiline output
* Last command output contains "rc:0"
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "This step phrase is close enough." | Behave decorator text must match the feature step exactly; near-duplicates create undefined or ambiguous steps. |
| "I can run `behave --dry-run tests/<suite>/` and it should work." | In this repo, run from the repo root with `tests/<suite>/features/` so Behave finds the steps directory. |
| "Smoke can just reuse the SSH helpers." | Smoke runs locally in-VM; importing shared SSH helpers there is the wrong harness and causes collisions. |
| "Any Bluefin-only tag name will trigger the smoke image guard." | `tests/smoke/features/environment.py` only checks for the exact `bluefin` tag, so smoke scenarios that should skip on dakota must use `@bluefin`, not `@bluefin_suite` or other variants. |

## Red Flags

- Adding a new generic step phrase without checking `tests/shared/ssh_steps.py` first
- Using `SSH command exit code is 0` or another non-canonical phrase in a feature file
- Running `behave --dry-run` against the suite root and getting `No steps directory`
- Importing `tests.shared.ssh_steps` into smoke steps or environment files
- Fixing a step mismatch in a feature file without updating this skill when the pattern was non-obvious

## Verification

- [ ] New or edited feature steps use existing canonical phrases where available
- [ ] `grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d` is empty
- [ ] `behave --dry-run tests/<suite>/features/` passes for each touched suite
- [ ] Skill content that depends on Behave step-matching behavior is source-verified against Context7 (`/behave/behave`)

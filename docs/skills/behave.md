---
name: behave-patterns
description: "Use when writing behave tests, scaffolding suites, or debugging step resolution in projectbluefin/testsuite."
metadata:
  type: reference
---

# Behave Patterns Reference

## When to Use

- Writing or extending behave `.feature` files in any suite
- Reusing or checking shared SSH step phrases
- Debugging `UndefinedStep`, `AmbiguousStep`, or dry-run failures
- Verifying suite-local step placement and cross-suite visibility

## When NOT to Use

- Smoke-suite GUI implementation details that belong in `docs/skills/gnome.md`
- Bootc / upgrade / rollback workflow rules that belong in `docs/skills/bootc.md`
- CI workflow ownership, runner, or reusable-action changes that belong in workflow skills

## Core Process

1. Read the target `.feature` file and the suite's `steps/*.py` before adding phrases.
2. Reuse `tests/shared/ssh_steps.py` for generic SSH command/assertion steps instead of duplicating helpers.
3. Keep step phrases unique within the loaded suite and check for collisions before committing.
4. Choose assertions that match the command shape: equality for single-line output, substring for multiline output.
5. Run `behave --dry-run` on the touched suite before pushing so undefined or ambiguous phrases fail locally.

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

For Bluefin desktop-model assertions, keep SSH-only Flatpak checks in the
`common` suite (remote configuration, bundled app IDs, `/usr/share/applications`
scans). GUI Flatpak-management coverage (Bazaar, Flatseal, per-app permissions)
belongs in the `software` suite.

When asserting Bluefin's bundled terminal app over SSH, accept either
`org.gnome.Ptyxis` or `com.raggesilver.BlackBox`. Images may ship either app ID
depending on the terminal packaging generation under test.

Import in suite `environment.py`:
```python
from tests.shared.ssh_steps import *  # noqa: F401,F403
```

Never duplicate `_ssh()` or generic step definitions in suite-specific `steps.py`.  
Default `run_ssh()` timeout: **60s** (not 30s — hardware commands are slow).

For common-suite systemd health checks, named oneshot services often finish in
`inactive (dead)` after a successful run. Do not assert `systemctl is-active`
alone for units like `dconf-update.service` or `ublue-system-setup.service`;
wrap the command with a fallback `systemctl show/status` probe and assert the
SSH return code instead of requiring persistent `active` state.

When a scenario is meant to fail on a bad command, never append `; true` (or
similar success-forcing trailers) to the SSH command. That masks the real exit
status and turns `SSH command return code is "0"` into a no-op. Use `2>&1` to
capture diagnostics, but preserve the original command's exit code.
## Common suite `ujust` recipe coverage

Keep SSH-based `ujust` recipe checks in `tests/common/features/common_ujust.feature`.
Prefer assertions against the wrapper's own output, not the underlying tool's raw
output — for example `ujust bios-info` prints `Manufacturer:` / `Release Date:`
labels itself, so checking for raw `dmidecode` keys like `Vendor` is brittle.

If a recipe is gated by `gum choose`, `pkexec`, or package-install side effects,
land the coverage as `@pending @wip` until a non-interactive harness exists.
Current example: `ujust toggle-updates` is interactive and flips `uupd.timer`
or `rpm-ostreed-automatic.timer` (not `ublue-update.timer`).

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

For MIME-handler coverage, prefer direct `subprocess.run(["xdg-mime", "query", "default", mime])` helpers in `tests/smoke/features/steps/steps.py` and assert the resolved `.desktop` file (or an allowed viewer set) instead of launching the app with `xdg-open`. This keeps smoke checks local to the VM and avoids window-management flake while still validating Bluefin's handler registration end to end.

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

## Bluefin desktop identity defaults: `gsettings get` vs `dconf read`

In the SSH-driven `common` suite, validate Bluefin desktop identity overrides with the API that matches the schema type:

- Use `gsettings get` for regular schemas shipped via `zz0-bluefin-modifications.gschema.override` (for example `org.gnome.desktop.interface accent-color` or `org.gnome.desktop.app-folders folder-children`).
- Use `dconf read` for relocatable schemas and extensions without XML schemas (for example custom media-key keybindings under `/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/`, Search Light under `/org/gnome/shell/extensions/search-light/`, and Ptyxis profile palette keys under `/org/gnome/Ptyxis/Profiles/<uuid>/`).

This keeps common-suite assertions aligned with how Bluefin actually ships those defaults in `projectbluefin/common`.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll just add a tiny local SSH helper." | Shared SSH phrases already exist in `tests/shared/ssh_steps.py`; duplication creates drift and inconsistent assertions. |
| "This phrase is descriptive enough; collisions are unlikely." | Behave loads all step files in a suite together, and duplicate phrases fail at runtime with `AmbiguousStep`. |
| "Equality is stricter, so I'll use it for all command output." | `... stripped "is"` only works for single-line output; multiline commands need substring assertions. |
| "A dry-run is overkill for a simple feature edit." | CI runs dry-run and will catch missing step definitions immediately; local dry-run is the cheap failure path. |

## Red Flags

- New suite-specific code duplicates `Run SSH command` or other shared SSH assertions
- A `.feature` file introduces a phrase with no matching `@step` decorator
- The same decorator text appears in multiple step files loaded by one suite
- A test checks relocatable dconf keys with the wrong tool (`gsettings` vs `dconf read`)
- A PR changes `tests/**` without a matching skill update

## Verification

- [ ] New or changed step phrases exist in the correct suite or shared helper module
- [ ] No duplicate step phrases exist in the touched suite
- [ ] `behave --dry-run` passes for the touched suite
- [ ] Output assertions match the command shape (single-line equality vs multiline substring)
- [ ] Any newly discovered reusable pattern is written back to a skill file in the same PR

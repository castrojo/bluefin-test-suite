# Bazaar Coverage Design

**Date:** 2026-06-30  
**Scope:** `projectbluefin/testsuite` — `software` suite + `tests/unit/`  
**Status:** Approved

## Problem

Bazaar ships three user-facing configuration layers — hooks (`hooks.py`), a blocklist (`blocklist.yaml`), and a curated storefront layout (`curated.yaml`) — none of which have any test coverage. A regression in any of these silently breaks the install-gate warnings, allows blocked apps, or wipes the curated storefront.

## Approach: Hybrid (unit + config + AT-SPI)

Three independent layers, each scoped to what it can reliably prove:

| Layer | What it proves | Files touched |
|---|---|---|
| Unit tests | Hook state machine correctness | `tests/unit/test_bazaar_hooks.py` |
| SSH/config checks | Deployment integrity on the image | `tests/software/features/bazaar_config.feature` |
| AT-SPI | Curated layout rendered; search pipeline works | `tests/software/features/bazaar_ui.feature`, `steps/steps.py` |

---

## Layer 1 — Unit tests (`tests/unit/test_bazaar_hooks.py`)

Call `hooks.py` as a subprocess with env vars injected, assert stdout. The hook script reads env vars and prints a single-word response (`ok`, `pass`, `deny`, `abort`). No mocking needed.

**Path to script:** `tests/common/features/../../..` is the wrong frame — the test must locate `hooks.py` relative to the testsuite root or accept a configurable path. Use the common fixture pattern already in `tests/unit/` (check existing conftest for any base-path helpers).

### Test cases

| Test name | `BAZAAR_HOOK_ID` | `BAZAAR_HOOK_STAGE` | Other env vars | Expected stdout |
|---|---|---|---|---|
| `test_jetbrains_setup_target` | `jetbrains-toolbox` | `setup` | `TS_TYPE=install`, `TS_APPID=com.jetbrains.IntelliJIdea` | `ok` |
| `test_jetbrains_setup_nontarget` | `jetbrains-toolbox` | `setup` | `TS_TYPE=install`, `TS_APPID=org.gnome.Calculator` | `pass` |
| `test_jetbrains_setup_android_studio` | `jetbrains-toolbox` | `setup` | `TS_TYPE=install`, `TS_APPID=com.google.AndroidStudio` | `ok` |
| `test_jetbrains_teardown_always_deny` | `jetbrains-toolbox` | `teardown` | — | `deny` |
| `test_jetbrains_dialog_cancel_aborts` | `jetbrains-toolbox` | `teardown-dialog` | `DIALOG_RESPONSE_ID=cancel` | `abort` |
| `test_jetbrains_dialog_accept` | `jetbrains-toolbox` | `teardown-dialog` | `DIALOG_RESPONSE_ID=run-ujust` | `ok` |
| `test_code_setup_vscode_target` | `code` | `setup` | `TS_TYPE=install`, `TS_APPID=com.visualstudio.code` | `ok` |
| `test_code_setup_vscodium_target` | `code` | `setup` | `TS_TYPE=install`, `TS_APPID=com.vscodium.codium` | `ok` |
| `test_code_setup_nontarget` | `code` | `setup` | `TS_TYPE=install`, `TS_APPID=org.gnome.Calculator` | `pass` |
| `test_code_teardown_always_deny` | `code` | `teardown` | — | `deny` |
| `test_code_dialog_cancel_aborts` | `code` | `teardown-dialog` | `DIALOG_RESPONSE_ID=cancel` | `abort` |
| `test_code_dialog_accept` | `code` | `teardown-dialog` | `DIALOG_RESPONSE_ID=download` | `ok` |
| `test_unknown_hook_passthrough` | `unknown-hook` | `setup` | — | `pass` |

**Implementation notes:**
- Env var names: prefix `BAZAAR_` is added by the hook script's own variable names. Inspect the script: `hook_id = os.getenv('BAZAAR_HOOK_ID')`, `stage = os.getenv('BAZAAR_HOOK_STAGE')`, `transaction_appid = os.getenv('BAZAAR_TS_APPID')`, `transaction_type = os.getenv('BAZAAR_TS_TYPE')`, `dialog_response_id = os.getenv('BAZAAR_HOOK_DIALOG_RESPONSE_ID')`.
- The script path must be resolved from repo root: `pathlib.Path(__file__).parents[3] / "system_files/bluefin/etc/bazaar/hooks.py"` — **but this is in `projectbluefin/common`, not testsuite**. Instead, the test should locate the script via `SSH` onto the running VM, or (simpler for unit tests) copy the script into `tests/unit/fixtures/hooks.py` during CI. **Preferred approach:** parametrize the script path via an env var `BAZAAR_HOOKS_SCRIPT`, default to the relative path from the repo root assuming common is a git submodule or adjacent checkout; if not found, skip the test with `pytest.skip("hooks.py not found")`.
- The subprocess call: `subprocess.run(["python3", script_path], env={...}, capture_output=True, text=True)`, assert `result.returncode == 0` and `result.stdout.strip() == expected`.

---

## Layer 2 — SSH/config checks (extend `bazaar_config.feature`)

Add these scenarios to the existing `bazaar_config.feature` file (all `@software` tagged, no new tag):

1. **`hooks.py` is present**  
   `test -f /etc/bazaar/hooks.py && echo present`

2. **`hooks.py` is valid Python**  
   `python3 -m py_compile /etc/bazaar/hooks.py && echo ok`

3. **Blocklist contains `com.vscodium.codium-insiders`**  
   `grep -q 'com.vscodium.codium-insiders' /etc/bazaar/blocklist.yaml && echo found`

4. **Blocklist contains `org.gnu.emacs`**  
   `grep -q 'org.gnu.emacs' /etc/bazaar/blocklist.yaml && echo found`

5. **Blocklist contains `app.devsuite.Ptyxis`**  
   `grep -q 'app.devsuite.Ptyxis' /etc/bazaar/blocklist.yaml && echo found`

6. **Hook ID `jetbrains-toolbox` declared in `bazaar.yaml`**  
   `grep -q 'jetbrains-toolbox' /etc/bazaar/bazaar.yaml && echo found`

7. **Hook ID `code` declared in `bazaar.yaml`**  
   `grep -q '  - id: code' /etc/bazaar/bazaar.yaml && echo found`

8. **Bazaar flatpak override grants `host-etc`**  
   `flatpak override --show io.github.kolunmi.Bazaar` output contains `host-etc`  
   — reuse the existing `Flatpak user override "{fragment}" is active for "{app_id}"` step, or add a system-override variant using `--system`.

**Note on step 8:** The override is a system override (baked into the image at `/usr/share/ublue-os/flatpak-overrides/`), not a user override. Use SSH: `cat /usr/share/ublue-os/flatpak-overrides/io.github.kolunmi.Bazaar` and assert `host-etc` is present.

---

## Layer 3 — AT-SPI (extend `bazaar_ui.feature` + `steps/steps.py`)

### New feature scenarios

Both scenarios use the existing `Background:` (launch + window accessible + main content loaded).

**Curated section headings visible:**
```gherkin
@retry @software @bazaar_ui @curated
Scenario: Curated "Bluefin Recommends" section heading is visible
  * Bazaar curated section heading "Bluefin Recommends" is visible

@retry @software @bazaar_ui @curated
Scenario: Curated "Browsers" section heading is visible
  * Bazaar curated section heading "Browsers" is visible
```

**Search pipeline:**
```gherkin
@retry @software @bazaar_ui @search
Scenario: Bazaar search for "Firefox" returns results
  * Activate Bazaar tab "Search"
  * Bazaar view "Search" is loaded
  * Type text: "Firefox" into Bazaar search field
  * Bazaar search results are not empty
```

### New step implementations

**`Bazaar curated section heading "{name}" is visible`**  
Walk the AT-SPI tree from the window: `findChildren(lambda n: n.showing and n.roleName == "label" and name in (n.name or ""))`. Poll up to 10s. The section title labels in Adwaita should be exposed as `label` or `heading` roles.

**`Type text: "{text}" into Bazaar search field`**  
Find an `entry` role node in the window (search input). Click it, type the text via uinput. Poll for the text to appear in the entry's `text` attribute.

**`Bazaar search results are not empty`**  
After typing, poll for any `list item` or `push button` role descendants in the window that are not tab buttons. Assert count > 0.

### @future additions

- App detail page: click a result tile, assert a "back" button and app name heading appear
- Hook install dialog: search for `IntelliJ IDEA`, click Install, assert `alert` dialog with "JetBrains" in body text

---

## File changes

| File | Change |
|---|---|
| `tests/unit/test_bazaar_hooks.py` | New file — 13 parametrized test cases |
| `tests/software/features/bazaar_config.feature` | +8 scenarios |
| `tests/software/features/bazaar_ui.feature` | +4 scenarios (2 curated, 1 search, 1 close-guard) |
| `tests/software/features/steps/steps.py` | +3 step definitions |
| `docs/skills/suite-map.md` | Update scenario counts |
| `QA-REVIEW.md` | Update scenario counts |
| `docs/skills/behave.md` | Note Bazaar curated/search steps |

---

## Acceptance criteria

- [ ] `python3 -m pytest tests/unit/test_bazaar_hooks.py -q` passes (or skips with message if hooks.py not found)
- [ ] `behave --dry-run tests/software/features/` passes with no undefined steps
- [ ] `ruff check tests/ --select E,F,W --ignore E501` clean
- [ ] Scenario counts updated in both `suite-map.md` and `QA-REVIEW.md`
- [ ] Both AI attribution trailers on every commit

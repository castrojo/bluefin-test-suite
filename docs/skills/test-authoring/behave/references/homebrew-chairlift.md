---
name: homebrew-chairlift
description: "ChairLift managed-cask coverage in the homebrew suite: AT-SPI root/label evidence, lane contract, and what upstream already tests."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Homebrew / ChairLift Integration

Read alongside the [behave SKILL](../SKILL.md). Covers the `homebrew` suite's
ChairLift scenarios (`chairlift.feature`, `chairlift_steps.py`), sourced from
the `projectbluefin/common` ChairLift rollout (`docs/skills/brew-lifecycle/`).

## The AT-SPI application root is the binary name, not the display name

ChairLift's accessible application root is **`chairlift`** — GTK derives it
from `g_get_prgname()`, i.e. the executable the cask links as
`${HOMEBREW_PREFIX}/bin/chairlift`. `ChairLift` (capital L) is only the
*frame* title; both spellings appear in the suite and are not interchangeable:

```gherkin
* Start application "chairlift" via "command"
* Wait until "ChairLift" "frame" appears in "chairlift"
```

qecore's `ROOT` fragment (` | in "{a11y_root_name}"`) and
`Application.instance` both resolve to
`dogtail.tree.root.application(<a11y_app_name>)`, so `environment.py` must
register `a11y_app_name="chairlift"`. The display name instead makes every UI
step raise "application not found" — indistinguishable from the app not
launching. Same rule as Ptyxis (`ptyxis` / frame title `Ptyxis`).

**So name what *is* on the bus when the root is missing.** A bare dogtail
`SearchError` reads identically whether the app crashed on start, was never
installed, a11y is off, or the registered name is wrong.
`chairlift_steps._chairlift_root()` wraps `context.chairlift.instance` and
re-raises an `AssertionError` appending
`tests.shared.a11y.accessible_application_names()`;
`environment.after_scenario` prints the same list for a failed
`@chairlift_ui` scenario, so the evidence survives failures inside
qecore-owned steps. The helper returns `["<AT-SPI unavailable: ...>"]` rather
than raising and the wrapper always re-raises: enriching a failure must never
turn it into a pass, nor hide it behind a second exception.

## Packaging scenarios must not depend on the UI launching

`chairlift.feature` has **no feature-level `Background`**. Only the two
`@chairlift_ui` scenarios run `Start application` / `Wait until ... frame`;
the cask-state, desktop-integration, and bootc-helper scenarios assert files
and services directly, so a UI regression or missing GNOME session cannot
fail all five at the same step and hide the packaging contract.

## Real accessible group labels, not the plan's placeholders

The plan assumed group titles `"Brew Packages"` / `"Flatpak Applications"`;
upstream ChairLift (`frostyard/chairlift`) uses neither.
`internal/navigation/navigation.go` defines the five configurable pages and
their group keys; the `PreferencesGroup` titles come from
`internal/views/*_page.go`:

| Config group key | Actual `SetTitle(...)` | Source |
|---|---|---|
| `applications_installed_group` | `Installed Applications` | `internal/views/applications_page.go:32` |
| `flatpak_user_group` | `User Flatpak Applications` | `internal/views/applications_page.go:61` |
| `flatpak_system_group` | `System Flatpak Applications` | `internal/views/applications_page.go:75` |
| `brew_group` | `Homebrew` | `internal/views/applications_page.go:95` |
| `brew_search_group` | `Search Homebrew` | `internal/views/applications_page.go:135` |
| `brew_bundles_group` | `Brew Bundles` | `internal/views/applications_page.go:166` |

"ChairLift exposes Brew and Flatpak management" therefore asserts `"Homebrew"`
and `"System Flatpak Applications"` (Bluefin enables both flatpak groups;
system scope matches how Bazaar-installed apps are managed). The five page
titles in `navigation.go`'s `Title` field matched the plan, so the
page-visibility scenario uses them verbatim.

## Page/group visibility is a sidebar-row check, not a content-stack check

`window.go` builds one `adw.ActionRow` per visible navigation item
(`row.SetTitle(item.Title)`), all shown at once in the `NavigationSplitView`
sidebar — independent of the content stack's current selection
(`w.contentPage.SetTitle(...)`). So the page steps need no navigation click,
and `navigation.VisibleItems()` omits `Features` entirely (its only group,
`features_group`, is disabled in Bluefin's `config.yml`) — the hide assertion
passes on absence, not on a hidden widget.

## Configuration-error toast text is a stable upstream string

`internal/config/diagnostic.go`'s `LoadError.ToastMessage()` renders
`"Configuration error: %s. All feature groups are disabled. Fix the
configuration file and restart ChairLift."` — a schema violation disables
every group. Match the substring `"Configuration error"`, not the sentence,
so the check survives a wording tweak to the `%s` detail. Bluefin's
`tests/check-chairlift-config` (`projectbluefin/common`) already fails closed
on upstream schema drift, so a match here means a config bug passed that gate.

## Desktop entry, icons, and binary paths (from the Homebrew cask, not the plan)

The cask (`frostyard/homebrew-tap` `Casks/chairlift.rb`) installs everything
user-scoped, matching the `BREW`/`STATE` path conventions already used
elsewhere in this suite:

- `~/.local/share/applications/org.frostyard.ChairLift.desktop` — the cask's
  `preflight` block rewrites `Exec=` to
  `${HOMEBREW_PREFIX}/bin/chairlift-wrapper` (a thin script sourcing `brew
  shellenv` before `exec chairlift "$@"`), so assert the whole line equals
  that path rather than merely containing `chairlift`. Compare via
  `Path(...).resolve()` on **both** sides: bootc images symlink `/home` →
  `/var/home`, so the cask may spell the prefix `/home/linuxbrew/...` while
  the suite's constant says `/var/home/...`. `realpath`-equality keeps the
  check exact (still rejecting other binaries, and `shlex.split` still
  rejecting injected arguments) without failing on the spelling.
- Three icons, not one: `~/.local/share/icons/hicolor/scalable/apps/
  org.frostyard.ChairLift.svg`, the `-flower` scalable variant, and
  `~/.local/share/icons/hicolor/symbolic/apps/org.frostyard.ChairLift-symbolic.svg`.
- `${HOMEBREW_PREFIX}/bin/chairlift` is the real binary (linked by `binary
  "chairlift"`); `chairlift-wrapper` is a separate linked script, not an
  alias — the desktop entry launches the wrapper so the app inherits the
  Homebrew-managed `PATH`/`brew shellenv` even when the session's lacks brew.
- `chairlift-updex-helper` is **not** linked by the cask
  (`frostyard/chairlift#54`): it needs PolicyKit policies a user-scope cask
  cannot install, so Bluefin has no updex coverage and leaves
  `features_group` disabled — see `chairlift_hides_page("Features")`.

## bootc staging: fixed helper path, one `exec`, authenticated defaults

`system_files/shared/usr/share/polkit-1/actions/org.frostyard.ChairLift.bootc.policy`
(in `projectbluefin/common`) pins `org.freedesktop.policykit.exec.path` to
`/usr/libexec/bootc-update-stage` with `<defaults>` `allow_any=auth_admin`,
`allow_inactive=auth_admin`, `allow_active=auth_admin_keep` — parse the XML
(`xml.etree.ElementTree`) rather than string-matching. `bootc-update-stage`
is a bash script whose only `exec` line is `exec /usr/bin/bootc upgrade
--download-only`; assert exactly one `exec` matching that argv, since the
helper's whole security contract is "download-only, no arguments forwarded."

## `brew-preinstall.service` success is four properties, not one

`brew-preinstall.service` (`projectbluefin/common`,
`system_files/shared/usr/lib/systemd/user/brew-preinstall.service`) is
`Type=oneshot` with `RemainAfterExit=true`. `Result=success` alone is **not**
evidence that it ran: a unit that never started also reports `Result=success`
(the property's default) while sitting at `ActiveState=inactive`, and a unit
whose file vanished reports `LoadState=not-found`. Assert all four in one
`systemctl --user show` call and compare the parsed `key=value` map:

| Property | Expected | Catches |
|---|---|---|
| `LoadState` | `loaded` | unit file missing from the image |
| `ActiveState` | `active` | never started (`RemainAfterExit` keeps a completed run active) |
| `SubState` | `exited` | still running, or dead |
| `Result` | `success` | `ExecStart` failed |

## Lane contract: verify preconditions, don't relocate the session

`brew-preinstall.service` is a **user** unit, so this suite is only meaningful
when a systemd user manager is actually running for the test user. The lane
(`projectbluefin/lab`'s `run-systemd-container-tests` template, coordinated
with `tests/homebrew/README.md`) must unmask and start `brew-setup.service`
and must enable lingering plus the test user's systemd user manager.

`environment.py` verifies that contract instead of trusting it, in order, and
every failure path raises `HomebrewLaneError` from `before_all`:

1. `systemctl --user show --property=Version` — probes the user manager.
2. `/var/home/linuxbrew/.linuxbrew/bin/brew` exists and is executable, with
   `brew-setup.service` named in the error: that unit provisions it and
   `brew-preinstall.service` cannot install a cask without it. Checking it
   *first* turns "Homebrew was never provisioned" into its own message
   instead of an opaque unit failure.
3. `systemctl --user start brew-preinstall.service`, then a `show` of
   `ActiveState`/`SubState`/`Result` — a `start` returning 0 without a
   completed run means the managed casks were never installed.

**Do not pin or rewrite `XDG_RUNTIME_DIR` from a test suite.** An earlier
revision required `/run/user/1000` and set it when unset; wrong layer. The
real requirement is a *reachable* user manager, which the probe establishes
for whatever uid the lane uses. Overwriting the variable relocates the a11y
and session bus out from under qecore/dogtail — breaking the UI steps this
suite exists to run — and hard-coding uid 1000 fails any lane with a
different test user, for no gain. Read it for diagnostics, never write it.

**Preconditions here fail the run; they never skip.** behave 1.3.x counts a
`before_all`/`before_scenario` exception as a hook failure, aborts, and exits
nonzero (`runner.py`: `hook_failures` feeds the final `failed` result). The
`context.failed_setup` → `scenario.skip()` pattern other suites use for
genuinely optional components (Podman Desktop on non-dx images) is wrong
here: a missing cask, desktop file, or dead service *is* the regression under
test, and skipping reports green. Only tag-driven skips remain, and this
suite carries none. Screenshot and timing helpers keep guarded imports
because losing an artifact degrades evidence without invalidating anything.
This suite runs through the lab lane, not the QEMU `e2e.yml` action — that
workflow masks `brew-setup.service` (#487), so `homebrew` fails at the
brew-binary precondition there by design. Keep it out of `e2e.yml`'s `suites`.

## What this suite does NOT cover (upstream's job)
`frostyard/chairlift` unit-tests config parsing (`internal/config`), Homebrew
search/trust/bundle logic (`internal/homebrew`), PolicyKit action shape, and
bootc progress streaming. This suite covers only Bluefin-specific packaging:
the managed-cask lifecycle, installed desktop/icon files, the UI rendered for
Bluefin's `config.yml`, and the fixed paths the bootc action depends on.

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
ChairLift scenarios (`chairlift.feature`, `chairlift_steps.py`) — sourced from
the `projectbluefin/common` ChairLift rollout (`feat/chairlift-rollout`,
`docs/skills/brew-lifecycle/SKILL.md`).

## The AT-SPI application root is the binary name, not the display name

ChairLift's accessible application root is **`chairlift`** — GTK derives it
from `g_get_prgname()`, i.e. the executable the cask links as
`${HOMEBREW_PREFIX}/bin/chairlift`. `ChairLift` (capital L) is only the
*frame* title. Both spellings appear in the suite and they are not
interchangeable:

```gherkin
* Start application "chairlift" via "command"
* Wait until "ChairLift" "frame" appears in "chairlift"
```

qecore's `ROOT` fragment (` | in "{a11y_root_name}"`) resolves straight to
`dogtail.tree.root.application(<a11y_root_name>)`, and
`Application.instance` resolves through the same `a11y_app_name`, so
`environment.py` must register `a11y_app_name="chairlift"`. Registering the
display name instead makes every UI step raise "application not found" — a
failure mode indistinguishable from the app not launching. Same rule as
Ptyxis (`a11y_app_name="ptyxis"`, frame title `Ptyxis`).

## Packaging scenarios must not depend on the UI launching

`chairlift.feature` has **no feature-level `Background`**. Only the two
`@chairlift_ui` scenarios run `Start application` / `Wait until ... frame`;
the cask-state, desktop-integration, and bootc-helper scenarios assert files
and services directly. A `Background` that launched the app would make a UI
regression (or a missing GNOME session) fail all five scenarios at the same
step, hiding whether the packaging contract itself still holds. Keep
non-UI packaging assertions launch-independent whenever the evidence lives on
disk or in systemd.

## Real accessible group labels, not the plan's placeholders

The original plan assumed group titles `"Brew Packages"` and `"Flatpak
Applications"`. Upstream ChairLift (`frostyard/chairlift`) does not use either
string. `internal/navigation/navigation.go` defines the five configurable
pages (`Applications`, `Maintenance`, `Updates`, `System`, `Features`) and
their group keys; the actual `PreferencesGroup` titles come from
`internal/views/*_page.go`:

| Config group key | Actual `SetTitle(...)` | Source |
|---|---|---|
| `applications_installed_group` | `Installed Applications` | `internal/views/applications_page.go:32` |
| `flatpak_user_group` | `User Flatpak Applications` | `internal/views/applications_page.go:61` |
| `flatpak_system_group` | `System Flatpak Applications` | `internal/views/applications_page.go:75` |
| `brew_group` | `Homebrew` | `internal/views/applications_page.go:95` |
| `brew_search_group` | `Search Homebrew` | `internal/views/applications_page.go:135` |
| `brew_bundles_group` | `Brew Bundles` | `internal/views/applications_page.go:166` |

`chairlift.feature`'s "ChairLift exposes Brew and Flatpak management" scenario
therefore asserts on `"Homebrew"` (the primary brew-management group) and
`"System Flatpak Applications"` (Bluefin enables both `flatpak_user_group` and
`flatpak_system_group`; system-scope matches how Bazaar-installed apps are
managed on Bluefin) — not the placeholder strings from the original plan.

The five page titles (`Applications`, `Updates`, `Maintenance`, `System`,
`Features`) in `navigation.go`'s `Title` field matched the plan exactly, so
`chairlift.feature`'s page-visibility scenario uses them verbatim.

## Page/group visibility is a sidebar-row check, not a content-stack check

`window.go` builds one `adw.ActionRow` per visible navigation item in the
sidebar (`row.SetTitle(item.Title)`), all shown simultaneously in the
`NavigationSplitView` sidebar — independent of which single page is currently
selected in the content stack (`w.contentPage.SetTitle(...)` only reflects the
*current* selection). `chairlift_shows_page`/`chairlift_hides_page` therefore
do not need to click any navigation row first: `navigation.VisibleItems()`
already omits `Features` entirely (its only group, `features_group`, is
disabled in Bluefin's `config.yml`), so no widget named `"Features"` exists in
the tree at all, and the assertion in `chairlift_hides_page` passes on
absence rather than on a hidden-but-present widget.

## Configuration-error toast text is a stable upstream string

`internal/config/diagnostic.go`'s `LoadError.ToastMessage()` renders
`"Configuration error: %s. All feature groups are disabled. Fix the
configuration file and restart ChairLift."` — a schema violation in
`config.yml` disables every group, not just the offending one. Search for the
substring `"Configuration error"`, not the full sentence, so the check
survives a wording tweak to the `%s` detail. Bluefin's own
`tests/check-chairlift-config` (`projectbluefin/common`) already fetches
upstream's live schema and fails closed on drift before this ever reaches a
booted image, so a nonempty match here would mean a load-bearing config bug
made it past that gate.

## Desktop entry, icons, and binary paths (from the Homebrew cask, not the plan)

The cask (`frostyard/homebrew-tap` `Casks/chairlift.rb`) installs everything
user-scoped, matching the `BREW`/`STATE` path conventions already used
elsewhere in this suite:

- `~/.local/share/applications/org.frostyard.ChairLift.desktop` — the cask's
  `preflight` block rewrites `Exec=` to
  `${HOMEBREW_PREFIX}/bin/chairlift-wrapper` (a thin script that sources
  `brew shellenv` before `exec chairlift "$@"`), so assert the whole line
  equals that path rather than merely containing `chairlift`. Compare it via
  `Path(...).resolve()` on **both** sides: bootc images symlink `/home` →
  `/var/home`, so the cask may spell the prefix `/home/linuxbrew/...` while
  the suite's constant says `/var/home/linuxbrew/...`. `realpath`-equality
  keeps the check exact (it still rejects any other binary, and `shlex.split`
  still rejects injected arguments) without failing on the symlink spelling.
- Three icons, not one: `~/.local/share/icons/hicolor/scalable/apps/
  org.frostyard.ChairLift.svg`, the `-flower` scalable variant, and
  `~/.local/share/icons/hicolor/symbolic/apps/org.frostyard.ChairLift-symbolic.svg`.
- `${HOMEBREW_PREFIX}/bin/chairlift` is the real binary (linked by `binary
  "chairlift"` in the cask); `chairlift-wrapper` is a separate linked script,
  not an alias — the desktop entry launches the wrapper specifically so the
  app inherits the Homebrew-managed `PATH`/`brew shellenv` even when the
  session's own `PATH` lacks brew.
- `chairlift-updex-helper` is **not** linked by the cask (see
  `frostyard/chairlift#54`): it needs PolicyKit policies a user-scope cask
  cannot install. Bluefin has no coverage for updex and does not enable
  `features_group` for this reason — see `chairlift_hides_page("Features")`
  above.

## bootc staging: fixed helper path, one `exec`, authenticated defaults

`system_files/shared/usr/share/polkit-1/actions/org.frostyard.ChairLift.bootc.policy`
(in `projectbluefin/common`) pins `org.freedesktop.policykit.exec.path` to
`/usr/libexec/bootc-update-stage` with `<defaults>` `allow_any=auth_admin`,
`allow_inactive=auth_admin`, `allow_active=auth_admin_keep` — parse the XML
(`xml.etree.ElementTree`) rather than string-matching, since the file is
small and stable. `bootc-update-stage` is a plain bash script whose only
`exec` line is `exec /usr/bin/bootc upgrade --download-only`; assert there is
exactly one `exec` invocation and it matches that argv exactly, since the
helper's entire security contract is "download-only, no caller arguments
forwarded."

## `brew-preinstall.service` success is four properties, not one

`brew-preinstall.service` (`projectbluefin/common`,
`system_files/shared/usr/lib/systemd/user/brew-preinstall.service`) is
`Type=oneshot` with `RemainAfterExit=true`. `Result=success` alone is **not**
evidence that it ran: a unit that never started also reports
`Result=success` (the property's default) while sitting at
`ActiveState=inactive`, and a unit whose file vanished from the image reports
`LoadState=not-found`. Assert all four in one `systemctl --user show` call
and compare the parsed `key=value` map:

| Property | Expected | Catches |
|---|---|---|
| `LoadState` | `loaded` | unit file missing from the image |
| `ActiveState` | `active` | never started (`RemainAfterExit` keeps a completed run active) |
| `SubState` | `exited` | still running, or dead |
| `Result` | `success` | `ExecStart` failed |

## Lane contract: uid 1000, `/run/user/1000`, and hard-failing preconditions

`brew-preinstall.service` is a **user** unit, so this suite is only meaningful
when a systemd user manager is actually running for the test user. The lane
(`projectbluefin/lab`'s `run-systemd-container-tests` template, coordinated
with `tests/homebrew/README.md`) must provide `brew-setup.service` unmasked
and started, `loginctl enable-linger bluefin-test`, `systemctl start
user@1000.service`, and `XDG_RUNTIME_DIR=/run/user/1000`.

`environment.py` pins that contract instead of trusting it: it rejects any
other `XDG_RUNTIME_DIR`, sets it when unset, and probes the manager with
`systemctl --user show --property=Version --value` before doing anything
else. Every failure path raises `HomebrewLaneError` from `before_all`.

**Preconditions here fail the run; they never skip.** behave 1.3.x counts a
`before_all`/`before_scenario` exception as a hook failure, aborts, and exits
nonzero (`runner.py`: `hook_failures` feeds the final `failed` result). The
older `context.failed_setup` → `scenario.skip()` pattern that other suites use
for genuinely optional components (Podman Desktop on non-dx images) is wrong
here: a missing cask, missing desktop file, or dead service *is* the
regression under test, and skipping it reports green. Only tag-driven
`@quarantine`/`@pending` skips remain, and this suite carries none. Screenshot
and timing helpers keep their guarded imports because losing an artifact
degrades evidence without invalidating an assertion.

This suite therefore runs **only** through the lab lane, never through the
QEMU `e2e.yml` action — that workflow masks `brew-setup.service` (#487), so
`homebrew` would fail at the first precondition there by design. Do not
advertise it in `e2e.yml`'s `suites` input.

## What this suite does NOT cover (upstream's job)
`frostyard/chairlift` unit-tests config parsing/validation (`internal/config`),
Homebrew search/trust/bundle logic (`internal/homebrew`), PolicyKit action
shape in the abstract, and bootc progress streaming in its own test suite.
This suite covers only Bluefin-specific packaging and configuration: the
managed-cask lifecycle, the installed desktop/icon files, the UI ChairLift
renders for Bluefin's actual `config.yml`, and the fixed paths the bootc
PolicyKit action depends on when installed on this image.

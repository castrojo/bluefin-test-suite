---
name: homebrew-chairlift
description: "ChairLift managed-cask coverage in the homebrew suite: accessible-label evidence and what upstream already tests."
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
  equals that path rather than merely containing `chairlift`.
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

## What this suite does NOT cover (upstream's job)

`frostyard/chairlift` unit-tests config parsing/validation (`internal/config`),
Homebrew search/trust/bundle logic (`internal/homebrew`), PolicyKit action
shape in the abstract, and bootc progress streaming in its own test suite.
This suite covers only Bluefin-specific packaging and configuration: the
managed-cask lifecycle, the installed desktop/icon files, the UI ChairLift
renders for Bluefin's actual `config.yml`, and the fixed paths the bootc
PolicyKit action depends on when installed on this image.

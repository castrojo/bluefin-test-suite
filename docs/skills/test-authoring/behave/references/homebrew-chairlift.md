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
ChairLift scenarios (`chairlift.feature`, `chairlift_steps.py`), sourced from the
`projectbluefin/common` ChairLift rollout (`docs/skills/brew-lifecycle/`).

## The AT-SPI application root is the binary name, not the display name

ChairLift's accessible application root is **`chairlift`** — GTK derives it from
`g_get_prgname()`, i.e. the executable the cask links as
`${HOMEBREW_PREFIX}/bin/chairlift`. `ChairLift` (capital L) is only the *frame*
*frame* title; both spellings appear in the suite and are not interchangeable:

```gherkin
* Start application "chairlift" via "command"
* Wait until "ChairLift" "frame" appears in "chairlift"
```

qecore's `ROOT` fragment (` | in "{a11y_root_name}"`) and `Application.instance`
both resolve to `dogtail.tree.root.application(<a11y_app_name>)`, so
`environment.py` must register `a11y_app_name="chairlift"`. The display name
instead makes every UI step raise "application not found" — indistinguishable
from the app not launching. Same rule as Ptyxis (`ptyxis` / frame `Ptyxis`).

**So name what *is* on the bus when the root is missing.** `Application.instance`
is a plain attribute: `None` from construction until a start step assigns
`get_root()`, and `None` again after close (`qecore/application.py:95,338,412`).
The absent-app state is therefore a `None` instance, not a raising lookup —
reading it only raises when `before_all` never registered the application.
`chairlift_steps._chairlift_root()` handles both and re-raises an
`AssertionError` naming the state plus
`tests.shared.a11y.accessible_application_names()`; `environment.after_scenario`
prints the same list for a failed `@chairlift_ui` scenario, so the evidence
survives failures inside qecore-owned steps. The helper returns `["<AT-SPI
unavailable: ...>"]` rather than raising and the wrapper always re-raises:
enriching a failure must never turn it into a pass, nor hide it behind another.

## Packaging scenarios must not depend on the UI launching

`chairlift.feature` has **no feature-level `Background`**. Only the two
`@chairlift_ui` scenarios run `Start application` / `Wait until ... frame`; the
cask-state, desktop-integration, and bootc-helper scenarios assert files and
services directly, so a UI regression or missing GNOME session cannot fail all
five at the same step and hide the packaging contract.

One more false-green guard lives in the lane: behave exits 0 when `--tags`
matches nothing, so `projectbluefin/lab`'s runner fails the workflow with `no
scenarios ran` on an empty tally. A typo'd `-p behave-tags` is a red lane.

## Real accessible group labels, not the plan's placeholders

The plan assumed group titles `"Brew Packages"` / `"Flatpak Applications"`;
upstream ChairLift (`frostyard/chairlift`) uses neither. Group keys come from
`internal/navigation/navigation.go`, titles from `internal/views/*_page.go`:

| Config group key | Actual `SetTitle(...)` | Source |
|---|---|---|
| `applications_installed_group` | `Installed Applications` | `internal/views/applications_page.go:32` |
| `flatpak_user_group` | `User Flatpak Applications` | `internal/views/applications_page.go:61` |
| `flatpak_system_group` | `System Flatpak Applications` | `internal/views/applications_page.go:75` |
| `brew_group` | `Homebrew` | `internal/views/applications_page.go:95` |
| `brew_search_group` | `Search Homebrew` | `internal/views/applications_page.go:135` |
| `brew_bundles_group` | `Brew Bundles` | `internal/views/applications_page.go:166` |

"ChairLift exposes Brew and Flatpak management" therefore asserts `"Homebrew"`
and `"System Flatpak Applications"` (Bluefin enables both flatpak groups; system
scope matches how Bazaar installs apps). The five page titles in
`navigation.go`'s `Title` matched the plan; used verbatim.

## Page/group visibility is a sidebar-row check, not a content-stack check

`window.go` builds one `adw.ActionRow` per visible navigation item
(`row.SetTitle(item.Title)`), all shown at once in the `NavigationSplitView`
sidebar — independent of the content stack's current selection
(`w.contentPage.SetTitle(...)`). So the page steps need no navigation click, and
`navigation.VisibleItems()` omits `Features` entirely (its only group,
`features_group`, is disabled in Bluefin's `config.yml`) — the hide assertion
passes on absence, not a hidden widget.

## Configuration-error toast text is a stable upstream string

`internal/config/diagnostic.go`'s `LoadError.ToastMessage()` renders
`"Configuration error: %s. All feature groups are disabled. Fix the
configuration file and restart ChairLift."` — a schema violation disables every
group. Match the substring `"Configuration error"`, not the sentence, so the
check survives a wording tweak to the `%s` detail. Bluefin's
`tests/check-chairlift-config` (`projectbluefin/common`) already fails closed on
schema drift, so a match here means a config bug passed that gate.

## Desktop entry and icons are asserted system-wide, not per-user

The cask's desktop entry and icons are **first-user-wins**, so asserting the
user copies would test the wrong thing. `Casks/chairlift.rb` writes
`#{Dir.home}/.local/share/{applications,icons}` — the home of whichever user
ran `brew bundle`. Homebrew has one shared prefix on Bluefin, so every later
user's `brew bundle` sees the cask installed, skips it, and that user gets no
launcher and no icon. `Path.home()` assertions pass on the machine that
provisioned the prefix and say nothing about anybody else.

`projectbluefin/common` ships the same upstream v0.10.1 artifacts image-side,
and those are what the steps assert: `/usr/share/applications/
org.frostyard.ChairLift.desktop`, plus `org.frostyard.ChairLift.svg` (resolves
`Icon=`) and `org.frostyard.ChairLift-flower.svg` under
`/usr/share/icons/hicolor/scalable/apps/`, and
`org.frostyard.ChairLift-symbolic.svg` under `.../symbolic/apps/`. The per-user
copies are deliberately **not** asserted — requiring them would fail a correct
multi-user image.

- `Exec=` is `/var/home/linuxbrew/.linuxbrew/bin/chairlift-wrapper`, a thin
  script (`brew shellenv`, then `exec chairlift "$@"`) that gives the app the
  Homebrew-managed `PATH` a GDM session lacks. Assert the whole line, not
  "contains `chairlift`", and compare `Path(...).resolve()` on **both** sides:
  bootc symlinks `/home` → `/var/home`, so a cask-written entry may spell it
  `/home/linuxbrew/...`. Realpath-equality keeps the check exact (other
  binaries still rejected, `shlex.split` still rejecting injected arguments).
- `environment.py` must hand qecore the **same** system-wide entry, because
  `Start application ... via "command"` reads `Exec=` from `desktop_file_path`.
  A user-home path there makes the `@chairlift_ui` scenarios unlaunchable for
  any test user who did not provision the prefix; a unit test asserts the two
  constants agree.
- `chairlift-updex-helper` is **not** linked by the cask
  (`frostyard/chairlift#54`): it needs PolicyKit policies a user-scope cask
  cannot install, so Bluefin has no updex coverage and disables
  `features_group` — see `chairlift_hides_page("Features")`.

## bootc staging: fixed helper path, one `exec`, authenticated defaults

`system_files/shared/usr/share/polkit-1/actions/org.frostyard.ChairLift.bootc.policy`
(in `projectbluefin/common`) pins `org.freedesktop.policykit.exec.path` to
`/usr/libexec/bootc-update-stage` with `<defaults>` `allow_any=auth_admin`,
`allow_inactive=auth_admin`, `allow_active=auth_admin_keep` — parse the XML
(`xml.etree.ElementTree`) rather than string-matching.

`bootc-update-stage`'s only `exec` line is `exec /usr/bin/bootc upgrade` —
**plain, no flags.** Assert exactly one `exec` matching that argv: pkexec runs
it as root, so "contains `bootc upgrade`" would also accept
`exec /some/other/tool "bootc upgrade"`.

`--download-only` is the trap, and asserting it was this suite's own earlier
bug. `bootc-upgrade(8)`: the image is retained "for the lifetime of this system
boot, but it will not be applied on reboot" — the user authenticates, pays a
full image pull, and reboots into the old deployment, while ChairLift's UI
(which re-reads `bootc status` for a staged deployment) shows nothing. It also
regresses `uupd`: on an already-staged deployment bootc calls
`change_finalization()`, so "check for updates now" would *cancel* an update
`uupd` had staged for shutdown. Plain `bootc upgrade` queues a staged
deployment for `ostree-finalize-staged` and unlocks one left download-only.

The contract is "stage only, forward no arguments, never these flags":
`--apply`/`--soft-reboot` (reboot), `--download-only` (never applies, re-locks
uupd's), `--from-downloaded` (only unlocks, never checks the registry). Compare
whole tokens and the `--flag=value` spelling, never substrings, and name the
offending flag — an exact-argv diff does not say why it is banned.

## `brew-preinstall.service` success is four properties, not one

`brew-preinstall.service` (`projectbluefin/common`,
`system_files/shared/usr/lib/systemd/user/brew-preinstall.service`) is
`Type=oneshot` with `RemainAfterExit=true`. `Result=success` alone is **not**
evidence that it ran: a unit that never started also reports `Result=success`
(the default) at `ActiveState=inactive`, and a unit whose file vanished reports
`LoadState=not-found`. Assert the first four in one `systemctl --user show`,
compare the parsed `key=value` map, and report the last two on failure:

| Property | Expected | Catches |
|---|---|---|
| `LoadState` | `loaded` | unit file missing from the image |
| `ActiveState` | `active` | never started (`RemainAfterExit` keeps a completed run active) |
| `SubState` | `exited` | still running, or dead |
| `Result` | `success` | `ExecStart` failed |
| `ConditionResult` | *diagnostic only* | `no` = systemd **skipped** the unit (`ConditionUser=!@system`, `ConditionPathExists=<brew binary>`): `start` exits 0 and the state is otherwise byte-identical to "never asked to run" |
| `ExecMainStatus` | *diagnostic only* | separates that skip from an `ExecStart` that ran and failed |

## Lane contract and fail-closed preconditions

The `homebrew` suite only means anything when the lane really provisioned
Homebrew and a systemd user manager, and `environment.py` verifies that rather
than trusting it. Why each precondition fails instead of skipping, and why a
suite must read `XDG_RUNTIME_DIR` and never write it:
[homebrew-lane-contract.md](homebrew-lane-contract.md).

## What this suite does NOT cover (upstream's job)

`frostyard/chairlift` unit-tests config parsing (`internal/config`), Homebrew
search/trust/bundle logic (`internal/homebrew`), PolicyKit action shape, and
bootc progress streaming. This suite covers only Bluefin-specific packaging: the
managed-cask lifecycle, the system-wide desktop/icon files, the UI rendered for
Bluefin's `config.yml`, and the fixed paths the bootc action depends on.

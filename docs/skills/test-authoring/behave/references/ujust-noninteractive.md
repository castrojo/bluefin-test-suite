---
name: ujust-noninteractive
description: "Which ujust recipes can be driven non-interactively, and why the rest stay @pending."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Ujust Noninteractive

## `toggle-updates` — non-interactive via `ACTION` (verified 2026-08)

`system_files/shared/usr/share/ublue-os/just/update.just` in
`projectbluefin/common` declares the recipe as `toggle-updates ACTION="prompt":`
and now reads the parameter through just's `{{ ACTION }}` interpolation (shebang
recipe bodies receive parameters only via interpolation, never as positional
arguments):

- `ujust toggle-updates enable` / `disable` / `cancel` (case-insensitive)
  select the action directly and skip both the bctl panel and the `gum choose`
  prompt. This is the non-interactive entry point tracked in
  `projectbluefin/testsuite#499`.
- Any other value — including the default `ACTION="prompt"` — keeps the
  interactive behavior: on images that ship `bctl` (bluefinctl), the recipe
  `exec`s `bctl --screen updates` and hands off to a GUI panel; otherwise it
  blocks on `gum choose`.

Asserting the timer state directly (`systemctl enable/disable uupd.timer`)
would test systemd, not the recipe, so it does not close the coverage gap.

Coverage lives in `tests/common/features/common_ujust.feature` behind a
`@requires_toggle_action` tag: the environment probes the recipe definition
with `ujust --show toggle-updates 2>/dev/null | grep -q 'ACTION_VALUE'`
rather than running `ujust toggle-updates cancel`. Running without a TTY
caused older unpatched recipes to fail in `gum choose` and set `SELECTED_OPTION=""`,
which hit `[[ "${SELECTED_OPTION}" == "Cancel" || "${SELECTED_OPTION}" == "" ]] && exit 0`,
falsely passing on unpatched images. Probing the recipe body for `ACTION_VALUE`
reliably skips the scenario on images that have not shipped the contract yet.
The scenario flips the update timer through the recipe itself (detecting
`uupd.timer`, falling back to `rpm-ostreed-automatic.timer`, matching the
recipe's own logic), asserts the state changed and the recipe's confirmation
output, then restores the original state so the scenario is repeatable.

## `bctl devmode` is the non-interactive contract for `toggle-devmode` (verified 2026-08)

`ujust toggle-devmode` (`system_files/bluefin/usr/share/ublue-os/just/system.just`
in `projectbluefin/common`) execs `bctl devmode --enable` whenever `bctl`
(bluefinctl) is present, before it ever reaches the interactive `gum choose`
stack-picker. `projectbluefin/bluefinctl`'s `devmode` Typer command already
ships `--enable`/`--disable` flags (`src/bluefinctl/cli.py`) that call
`bluefinctl.core.devmode.toggle_devmode()` headlessly — this closes the
"no non-interactive entry point" gap tracked in `projectbluefin/testsuite#500`.

Coverage lands in `tests/common/features/common_devmode.feature` in two parts:

- **Presence + idempotent state-check (`@requires_bctl`):** `bctl devmode --help`
  advertises both flags, and `bctl devmode --disable` on an already-inactive
  VM takes bluefinctl's read-only branch (checks `_check_devmode_active()`,
  prints `Developer mode is already inactive.`, returns) — this exercises the
  state-check without mutating anything. Assert the full sentence, not the exit
  code: `bctl devmode` returns 0 on both branches, so rc alone proves nothing.
- **Group mutation (`@pending @wip`):** `bctl devmode --enable` calls
  `pkexec usermod` to add the `docker`/`incus-admin`/`libvirt`/`dialout`
  groups. `pkexec` requires an authentication agent registered against a real
  login session; a plain SSH connection has none, so the mutating branch
  cannot be driven headlessly in the current SSH-only harness. This is a CI
  polkit/session gap, not a recipe interface gap like `toggle-updates` above (same file) —
  do not conflate the two when triaging failures here.

See [`bctl-devmode.md`](bctl-devmode.md) for the
`@requires_bctl` gate, the content-vs-exit-code assertion rule, and the
`@devmode_cleanup` teardown hook.

---
name: ujust-noninteractive
description: "Which ujust recipes can be driven non-interactively, and why the rest stay @pending."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Ujust Noninteractive

## `toggle-updates` is not drivable non-interactively (verified 2026-08)

`system_files/shared/usr/share/ublue-os/just/update.just` in
`projectbluefin/common` declares the recipe as `toggle-updates ACTION="prompt":`
but the recipe body never reads `ACTION`. The body has two branches:

```bash
# Open the bluefinctl Updates panel when available
if command -v bctl &>/dev/null; then
    exec bctl --screen updates
fi
...
SELECTED_OPTION="$(gum choose --header="Toggle automatic updates?" "Enable" "Disable" "Cancel")"
```

Both branches are untestable, for different reasons:

- On images that ship `bctl` (bluefinctl), the recipe `exec`s
  `bctl --screen updates` and hands off to a GUI panel. The recipe never
  reaches the timer logic and there is nothing for SSH to assert.
- Only when `bctl` is absent does the recipe fall back to the shell path, and
  that fallback blocks on `gum choose`. This is the branch that hangs a
  non-interactive run.
- `ujust toggle-updates Enable` accepts the argument on either path and ignores
  it; the parameter is decorative, so no flag-based non-interactive entry point
  exists today.
- Asserting the timer state directly (`systemctl enable/disable uupd.timer`)
  tests systemd, not the recipe, so it does not close this coverage gap.

Keep the scenario `@pending @wip` until `projectbluefin/common` makes `ACTION`
actually select `Enable`/`Disable`/`Cancel` without a prompt. That is a
`projectbluefin/common` interface change and needs maintainer acceptance
(`projectbluefin/testsuite#499`) before any testsuite implementation lands.

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

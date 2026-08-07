---
name: bctl-devmode
description: "Driving bluefinctl devmode non-interactively, and the assertion traps around it."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Bctl Devmode

## `bctl` is a Homebrew binary — gate on it, do not assume it

`bluefinctl` ships through
`system_files/shared/usr/share/ublue-os/homebrew/preinstall.d/bluefinctl.Brewfile`
in `projectbluefin/common`, and `e2e.yml` boots the QEMU VM with
`systemd.mask=brew-setup.service`, hand-installing only `fzf bat eza fd ripgrep
starship`. **`bctl` is therefore absent in QEMU CI**, and any scenario that
shells out to it without a gate fails on `command -v bctl` rather than on the
behaviour it claims to test.

Use the `@requires_bctl` tag. `tests/common/features/environment.py` resolves it
once per run (`_has_bctl`, mirroring `_has_brew`) and skips with an explicit
reason. A visible skip is honest; a green run against a binary that does not
exist is not.

## Assert output content, not the exit code

`bctl devmode --disable` returns 0 on both the read-only branch and the
mutating branch, so the return code proves nothing on its own. Assert the
sentence bluefinctl actually prints (`src/bluefinctl/cli.py`):

```gherkin
* Run SSH command: "bctl devmode --disable"
* SSH command return code is "0"
* SSH command output contains "Developer mode is already inactive"
```

## Absence checks must assert a return code, never an empty string

`groups` output is the devmode state, and `SSH command output does not contain
"docker"` passes vacuously when the output is empty — which is exactly what an
SSH transport failure (`rc 255`) produces. Drive the match in the shell and
assert the code instead:

```gherkin
* Run SSH command: "groups"
* SSH command return code is "0"
* SSH command output is not empty
* Run SSH command: "groups | tr ' ' '\n' | grep -qxE 'docker|incus-admin|libvirt|dialout'"
* SSH command return code is "1"
```

`rc 1` means "grep ran and matched nothing"; `rc 255` fails the assertion loudly.
Checking only `docker` is also wrong — bluefinctl's `DEVMODE_GROUPS` is all four
(`src/bluefinctl/core/devmode.py`), so a user in `dialout` alone is already
"active" and `--disable` would take the mutating `pkexec` branch.

## State-mutating scenarios clean up in `after_scenario`, not trailing steps

The devmode enable scenario carries `@devmode_cleanup`; `after_scenario` in
`tests/common/features/environment.py` runs `bctl devmode --disable` for that
tag. Trailing cleanup steps only run when every earlier step passed, so a
mid-scenario failure would leak an enabled devmode into the retry. The hook
skips scenarios whose status is `skipped` (they never mutated anything) and
swallows its own errors so teardown cannot mask the real failure.

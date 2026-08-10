---
name: homebrew-lane-contract
description: "How the homebrew suite verifies its lane preconditions: user-manager and brew probes that fail rather than skip, and why XDG_RUNTIME_DIR is read-only to a suite."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Homebrew lane contract

Read alongside the [behave SKILL](../SKILL.md) and
[homebrew-chairlift.md](homebrew-chairlift.md). Covers what the `homebrew`
suite's `environment.py` demands of the lane, and what it must never do to
the lane in return.

## Lane contract: verify preconditions, don't relocate the session

`brew-preinstall.service` is a **user** unit, so this suite is only meaningful
when a systemd user manager is actually running for the test user. The lane
(`projectbluefin/lab`'s `run-systemd-container-tests` template, coordinated with
`tests/homebrew/README.md`) must unmask and start `brew-setup.service` and run a
systemd user manager reachable at the `XDG_RUNTIME_DIR` the behave process sees.
Neither is true of the template today — that README's "What the lab lane must
add" section carries the live values and line numbers.

`environment.py` verifies that contract instead of trusting it, raising
`HomebrewLaneError` from `before_all` in this order: probe the user manager
(`systemctl --user show --property=Version`); require the brew binary to exist
and be executable, naming `brew-setup.service`, so "Homebrew was never
provisioned" gets its own message instead of an opaque unit failure; then start
`brew-preinstall.service` and `show` its state, because a `start` returning 0
without a completed run means the managed casks were never installed.

**Do not pin or rewrite `XDG_RUNTIME_DIR` from a test suite.** An earlier
revision required `/run/user/1000` and set it when unset — wrong layer, and the
reason first given for reverting it was also wrong. Rewriting the variable does
**not** move the a11y or session bus here: the lane pins both with absolute
`DBUS_SESSION_BUS_ADDRESS`/`AT_SPI_BUS_ADDRESS` values that do not follow it.
What it does move is `systemctl --user`, which reaches the manager through
`$XDG_RUNTIME_DIR/systemd/private` and ignores those bus variables — verified on
systemd 260.2: a bogus `DBUS_SESSION_BUS_ADDRESS` still works, a bogus
`XDG_RUNTIME_DIR` fails with `Failed to connect to user scope bus via local
transport`. So a suite that rewrites it probes a *different* manager than the
lane started, and hard-coding uid 1000 fails any lane with another test user.
Both lookups must agree; only the lane can make them agree. Read, never write.

**Preconditions here fail the run; they never skip.** behave 1.3.x counts a
`before_all`/`before_scenario` exception as a hook failure, aborts, and exits
nonzero (`runner.py`: `hook_failures` feeds the final `failed` result). The
`context.failed_setup` → `scenario.skip()` pattern other suites use for
genuinely optional components (Podman Desktop on non-dx images) is wrong here: a
missing cask, desktop file, or dead service *is* the regression under test, and
skipping reports green. Only tag-driven skips remain, and this suite carries
none. Screenshot and timing helpers keep guarded imports because losing an
artifact degrades evidence without invalidating anything. This suite targets the
lab lane, not the QEMU `e2e.yml` action, which masks `brew-setup.service` (#487)
— `homebrew` fails there at the brew-binary precondition by design, so keep it
out of `e2e.yml`'s `suites`.

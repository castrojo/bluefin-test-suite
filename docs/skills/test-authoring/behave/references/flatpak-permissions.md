---
name: flatpak-permissions
description: "Flatpak per-app permission coverage via the CLI."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Flatpak Permissions

Lessons from #710. Read alongside the Flatpak section of the behave SKILL.

## `flatpak permissions <table>` succeeds for tables that do not exist

`flatpak permissions no-such-table` exits 0 and prints nothing, so a return-code-only
assertion never proves the table exists. The same is true over D-Bus:
`org.freedesktop.impl.portal.PermissionStore.List` and `.Lookup` do not distinguish a
missing table either. Assert on output content — rows are tab separated with the table
name in column 0, and an existing-but-empty table prints the `No permissions` sentinel.

To prove the documents backend is actually present, call
`org.freedesktop.portal.Documents.GetMountPoint`; it is the only call that fails when
the portal is absent (it returns `(b'/run/user/<uid>/doc',)` when present). The step
`Flatpak documents portal reports a mount point` wraps it.

## "No overrides exist" must cover `[Environment]`, not just `[Context]`

`flatpak override --user --show` keyfiles have both a `[Context]` and an
`[Environment]` section. A check that only walks `[Context]` keys reports "no
overrides" while `BLUEFIN_TESTSUITE=1` is still injected into the sandbox. Parse
section headers and treat any entry in either section as an override.

## Cleanup belongs in `after_scenario`, not in trailing steps

A `Then Reset flatpak user overrides for ...` step only runs when every preceding step
passed. One failure leaves the synthetic override installed and contaminates the next
scenario and every rerun. Put the reset in `after_scenario` in
`tests/software/features/environment.py` (`_reset_flatpak_permission_probe`) so it runs
unconditionally; the trailing step may stay as an in-scenario assertion.

## A sweep that passes on an empty install set is not coverage

`Every installed flatpak app exposes a parsable permission set` iterates `flatpak list`,
and CI — where `flatpak-preinstall.service` is masked and `/var/lib/flatpak` is not
seeded — is exactly the empty-set case, so the scenario was always green while
asserting nothing. It is `@pending` on #706 until the lab seeds a guaranteed-present
Flatpak. Never ship a scenario whose only CI behaviour is a vacuous pass; tag it with a
named blocker instead.

## `_flatpak` takes `context` first

`tests/software/features/steps/steps.py` defines `_flatpak(context, args, timeout=10)`.
Calling `_flatpak([...])` raises `TypeError` at runtime, and unit mocks that accept
`*args` hide it. Unit-test the call signature (`inspect.signature`) or assert the mock
was called with `context` as the first positional argument.

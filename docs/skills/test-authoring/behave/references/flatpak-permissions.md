---
name: flatpak-permissions
description: "Flatpak per-app permission coverage via the CLI."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Flatpak Permissions

## Flatpak per-app permissions: assert via CLI, not Flatseal's GUI

Flatseal (`com.github.tchx84.Flatseal`) is only a front end over `flatpak override`
and the portal permission store. Cover per-app permission behaviour with the CLI —
it needs no desktop session and no AT-SPI:

| What Flatseal shows | CLI assertion surface |
|---|---|
| Per-app toggles the user has changed | `flatpak override --user --show <app>` |
| Effective manifest permissions | `flatpak info --show-permissions <app>` |
| Portal grants (documents, notifications, background) | `flatpak permissions [<table>]` |

Two properties make these scenarios survivable in CI, where
`flatpak-preinstall.service` is masked and `/var/lib/flatpak` is not seeded
(the reason `tests/smoke/features/flatpak_permissions.feature` is quarantined):

1. **`flatpak override --user` accepts an application ID that is not installed.**
   Use a synthetic ID such as `org.projectbluefin.TestsuitePermissionProbe` so the
   round-trip neither depends on nor clobbers real installed apps. Always finish the
   scenario with `Reset flatpak user overrides for ...`.
2. **A sweep that passes on an empty install set is not coverage.** `Every installed
   flatpak app exposes a parsable permission set` iterates `flatpak list`, and CI is
   exactly the empty-set case, so the scenario was always green while asserting
   nothing. It is `@pending` on #706 until the lab seeds a guaranteed-present Flatpak.
   Never ship a scenario whose only CI behaviour is a vacuous pass; tag it with a
   named blocker instead.

`flatpak override --show` emits a keyfile, not flag syntax:

```ini
[Context]
sockets=!wayland;
devices=all;

[Environment]
BLUEFIN_TESTSUITE=1
```

Parse it (`parse_flatpak_context` in
`tests/software/features/steps/flatpak_permissions_steps.py`) instead of matching raw
lines. Comparing whole stripped lines against bare key names (`"filesystems"`) never
matches `filesystems=home;` and passes falsely — the same class of bug as
`grep -c ... || echo 0`. Split on the first `=` and compare the key.

## Software suite is not wired for shared SSH steps

`tests/software/features/environment.py` never sets `context.ssh_key`,
`context.ssh_user`, or `context.vm_ip`, so `Run SSH command` from
`tests/shared/ssh_steps.py` raises `AttributeError` there even though the module is
star-imported. New software-suite steps must go through the suite's own `_flatpak`
helper (or another helper that builds its own SSH invocation from `SSH_KEY`/`VM_IP`/
`VM_USER`/`SSH_PORT` env vars), not the shared SSH steps.

## `@flatpak_cli` marks image-agnostic software scenarios

`tests/software/features/environment.py` skips any `@software` scenario when Bazaar
(`io.github.kolunmi.Bazaar`) is absent — unless the scenario also carries
`@flatpak_cli`. Tag CLI-only, image-agnostic software scenarios with `@flatpak_cli`
so they still run on gnomeos and other non-Bluefin images.

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

## `_flatpak` takes `context` first

`tests/software/features/steps/steps.py` defines `_flatpak(context, args, timeout=10)`.
Calling `_flatpak([...])` raises `TypeError` at runtime, and unit mocks that accept
`*args` hide it. Unit-test the call signature (`inspect.signature`) or assert the mock
was called with `context` as the first positional argument.

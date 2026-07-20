---
name: actions-repo
description: "Detailed guidance for testsuite contributors: load when the core contributing skill routes you here."
metadata:
  type: reference
  audience: agents
  maturity: stable
---

# Working in <image-org>/actions

## Working in <image-org>/actions

When fixing promote bugs or shared workflow issues, changes go to `~/src/actions`.

### Consumer validation — exact PR body format

Every PR to `<image-org>/actions` that touches a reusable workflow or composite action requires three lines in the PR body. The check uses an exact regex — the URL must be on the **same line** as the label (not a heading with the URL below):

```
Consumer PR: https://github.com/<image-org>/bluefin/pull/672
Consumer CI run: https://github.com/<image-org>/bluefin/actions/runs/27979754906
Out-of-org consumer impact: N/A. aurora and bazzite do not call this workflow.
```

The regex for `Consumer PR:` requires `^Consumer PR:\s+https://github\.com/<image-org>/(bluefin|bluefin-lts|dakota)/pull/[0-9]+`. A markdown heading (`## Consumer PR`) with the URL on the next line fails validation.

For the consumer PR URL, use an open promote PR (`gh pr list --repo <image-org>/bluefin | grep promote`). For the run URL, use the most recent promote run on that branch.

### v1 tag — no SHA bumps needed in consumer repos

`<image-org>/actions` auto-updates the mutable `v1` tag on every push to `main` via `update-v1-tag.yml`. Consumer repos (`bluefin`, `bluefin-lts`, `dakota`) reference `@v1` — fixes propagate automatically on the next promote run. Do not open Renovate-style SHA-bump PRs in consumer repos for actions changes.

### CI sometimes doesn't trigger on PR open

The `<image-org>/actions` repo occasionally fails to queue CI when a PR is first opened. If `gh run list --repo <image-org>/actions --branch <branch>` returns empty after 2 minutes:

```bash
git push --force-with-lease   # force-push (no change needed) — re-triggers all PR workflows
```

Close-and-reopen also works (`gh pr close N && gh pr reopen N`) but force-push is faster.



### CI checks (`.github/workflows/pr-validate.yml` — must pass)

```bash
# Ruff lint
ruff check tests/ --select E,F,W --ignore E501

# Python syntax
python3 -m py_compile $(find tests/ -name '*.py' | tr '\n' ' ')
```

CI also runs `behave --dry-run` across all suites in a Fedora 41 container. This catches undefined step patterns (feature file uses a phrase with no matching `@step` decorator). **If you add a step phrase to a `.feature` file you must implement the `@step` before pushing.**

To replicate locally (requires Fedora or the runner container `ghcr.io/<image-org>/testsuite:runner`):
```bash
for suite in tests/*/features/; do
  PYTHONPATH=. python3 -m behave "$suite" --dry-run --no-capture
done
```

**GNOME suite dry-run requires a D-Bus session.** Suites that import `qecore.sandbox` load `gi.repository.Atspi` at import time. Without an AT-SPI bus, `libatspi` calls `g_error()` → `SIGTRAP` even during `--dry-run`.

Required packages (Fedora 41):
```bash
dnf install -y python3-gobject at-spi2-core dbus-daemon gtk3 gsettings-desktop-schemas
```

Run inside a session bus:
```bash
cat > /tmp/dry-run.sh << 'DRYEOF'
/usr/libexec/at-spi-bus-launcher --launch-immediately &
sleep 1
for suite in tests/*/features/; do
  PYTHONPATH=. python3 -m behave "$suite" --dry-run --no-capture
done
DRYEOF
chmod +x /tmp/dry-run.sh
dbus-run-session -- bash /tmp/dry-run.sh
```

Key package notes:
- `dbus-run-session` is in the `dbus-daemon` package on Fedora 41 (not `dbus-tools` or `dbus`)
- `at-spi-bus-launcher` is at `/usr/libexec/at-spi-bus-launcher` from `at-spi2-core`
- PyGObject from Ubuntu always fights ABI with the GHA toolcache Python — always use a Fedora container

### Recommended local checks (not in CI but catch common mistakes)

```bash
# Duplicate step patterns (replace <suite> with the suite you touched)
grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d

# @future inventory (verify no accidental tag changes)
just list-stubs
```

All CI checks must pass cleanly before pushing. Local checks should also be clean.

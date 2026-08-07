---
name: shared-ssh
description: "Shared SSH helpers and where to use them."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Shared Ssh

## Shared SSH helpers

`tests/shared/ssh_steps.py` is canonical for:
- `Bluefin VM is booted and reachable over SSH`
- `Run SSH command: "<cmd>"`
- `SSH command return code is "<code>"`
- `SSH command output "is" "<expected>"`
- `SSH command output stripped "is" "<expected>"`
- `SSH command output contains "<text>"`
- `SSH command output does not contain "<text>"`
- `SSH command output is not "<value>"`
- `SSH command output is not "<a>" and not "<b>"`
- `SSH command output is not empty`

For Bluefin desktop-model assertions, keep SSH-only Flatpak checks in the
`common` suite (remote configuration, bundled app IDs, `/usr/share/applications`
scans). GUI Flatpak-management coverage (Bazaar, Flatseal, per-app permissions)
belongs in the `software` suite.

When asserting Bluefin's bundled terminal app over SSH, accept either
`org.gnome.Ptyxis` or `com.raggesilver.BlackBox`. Images may ship either app ID
depending on the terminal packaging generation under test.

Import in suite `environment.py`:
```python
from tests.shared.ssh_steps import *  # noqa: F401,F403
```

## Importing the steps is only half the contract

`run_ssh()` reads its connection details from **`context`**, not from the
environment. A suite that star-imports `ssh_steps` must also populate them in
`before_all`, or every SSH step raises `AttributeError` at runtime:

```python
def before_all(context):
    context.vm_ip = os.environ.get("VM_IP", "")
    context.ssh_user = os.environ.get("VM_USER", "bluefin-test")
    context.ssh_key = os.environ.get("SSH_KEY", "/home/bluefin-test/.ssh/id_ed25519")
    context.ssh_port = os.environ.get("SSH_PORT", "")  # optional
```

Importing the steps registers the step phrases, so `behave --dry-run` passes and
the gap stays invisible until the suite runs against a real VM.

Unit tests cannot catch this either: they stub `tests.shared.ssh_steps` wholesale
(see [unit-test-module-stubs](unit-test-module-stubs.md)), so the real
`run_ssh()` never executes. Assert on the suite's `before_all` instead — verify
it sets the attributes `run_ssh()` requires.

**Never read connection details from `os.environ` inside a suite-local helper.**
A private helper that resolves `VM_IP`/`SSH_KEY` itself will work while the
shared steps in the same suite fail, which masks the missing wiring and creates
two sources of truth. Resolve once in `before_all`, onto `context`.

Never duplicate `_ssh()` or generic step definitions in suite-specific `steps.py`.  
Default `run_ssh()` timeout: **60s** (not 30s — hardware commands are slow).
In `tests/common/features/`, `environment.py` already exports
`XDG_RUNTIME_DIR`, `DBUS_SESSION_BUS_ADDRESS`, and `WAYLAND_DISPLAY` for every
SSH command via `ssh_command_prefix`. Prefer plain `systemctl --user`,
`gsettings`, and `gdbus` commands there instead of manually sourcing
`/tmp/session.env` inside each scenario.

For common-suite systemd health checks, oneshot services finish in `inactive (dead)`
after a successful run — their `ActiveState` is `inactive`, not `active`. Do NOT
assert `ActiveState==active` for units like `dconf-update.service`,
`ublue-system-setup.service`, `ublue-user-setup.service`, or
`bootc-unified-storage.service`. Use `Result` instead:

```gherkin
* Run SSH command: "systemctl show ublue-system-setup.service --property=Result --value"
* SSH command return code is "0"
* SSH command output stripped "is" "success"
```

The `Result` property is `success` when the service exited cleanly, `failed` if it
errored, and `exit-code` / `signal` for specific exit failures. Asserting
`ActiveState==active` on a completed oneshot always returns `inactive` and causes
false failures in QEMU CI even when the service ran correctly.

**Keep `@quarantine`** for services that are masked or disabled in the CI
`KERNEL_ARGS` (e.g. `flatpak-preinstall.service`) — those cannot be unquarantined
until the image-level masking is removed.

When a scenario is meant to fail on a bad command, never append `; true` (or
similar success-forcing trailers) to the SSH command. That masks the real exit
status and turns `SSH command return code is "0"` into a no-op. Use `2>&1` to
capture diagnostics, but preserve the original command's exit code.

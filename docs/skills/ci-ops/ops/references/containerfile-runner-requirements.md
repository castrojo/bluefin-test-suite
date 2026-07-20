---
name: containerfile-runner-requirements
description: "Deep dive: Containerfile.runner requirements"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Containerfile Runner Requirements

## Containerfile.runner requirements

When `container/Containerfile.runner` is changed, dispatch `build-runner.yml` to rebuild and push before dispatching test runs.

**Required packages** (all must be in the `microdnf install` block):

| Package | Why |
|---|---|
| `gobject-introspection` | Owns `xlib-2.0.typelib` and many others; NOT a weak dep on Fedora-minimal with `--setopt=install_weak_deps=0` |
| `procps-ng` | Provides `pgrep`/`pkill`; not in fedora-minimal |
| `gcc`, `python3-devel` | Required to build `python-uinput` from source |
| `dbus-tools` | Provides `dbus-uuidgen` (not `dbus-daemon`) |

**machine-id must be seeded:**
```dockerfile
RUN dbus-uuidgen > /etc/machine-id && \
    mkdir -p /var/lib/dbus && \
    ln -sf /etc/machine-id /var/lib/dbus/machine-id
```
`fedora-minimal` ships `/etc/machine-id` as a zero-length file. D-Bus refuses to start without a valid 32-hex UUID.

**setuptools must be explicit:**
`pkg_resources` (used by qecore) is part of `setuptools`, not installed by default in Python 3.14. Add `setuptools` to the pip install block.

**stop_display_manager must be wrapped:**
`qecore-headless` cleanup calls `stop_display_manager()` after the user script. Inside the runner container there is no systemd, so it raises `CalledProcessError`. Wrap it:
```python
try:
    if self.enable_stop or self.user_script_exit_code != 0:
        self.display_manager_control.stop_display_manager()
except Exception:
    pass
```
Without this, the container exits 1 even when all tests pass.

**rawinput ponytail None-guard:**
`sandbox.before_scenario` → `overview_action("hide")` → `rawinput.click()` → `ponytail_interface.window_list` crashes when ponytail is unreachable. Patch `ponytail_helper.py` in the runner image to return `None` instead of raising, and add a `None` guard before `.window_list`.

**qecore-headless env retrieval:**
`qecore-headless` reads `/proc/<pid>/environ` for GNOME session env. With `--pid=host`, this fails with `Permission denied`. The code must handle this gracefully (warn + continue) rather than `sys.exit(1)`.

---

---
name: kde-faillog
description: "Failure-artifact bundle for KDE/Plasma scenarios, modelled on ChromeOS Tast faillog."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# KDE Fail Log

`tests/shared/kde_faillog.py` captures a bundle of diagnostic artifacts whenever a
KDE/Plasma behave scenario fails. It is intended to be called from a suite's
`after_scenario` hook.

## When it runs

Collection triggers for scenario statuses `failed`, `error`, and `hook_error`.
This includes failures that occur inside `before_scenario`, because behave still
invokes `after_scenario` after a hook error.

## Collected artifacts

| File | Source | Notes |
|---|---|---|
| `atspi_tree.txt` | VM over SSH | `pyatspi` accessibility tree walk. |
| `journalctl.log` | VM over SSH | `journalctl -b --no-pager --lines=N`. |
| `kwin_support_info.txt` | VM over SSH | `org.kde.KWin.supportInformation()`. |
| `plasma_layout.js` | VM over SSH | `org.kde.PlasmaShell.dumpCurrentLayoutJS()`. |
| `coredumpctl.txt` | VM over SSH | `coredumpctl list --no-pager --lines=N`. |
| `qemu_screendump.png` | Runner host | QEMU monitor screendump via `tests/shared/qemu_screendump.py`. |
| `manifest.json` | Bundle | Metadata and per-collector success/error records. |

## Fault isolation

Each collector runs independently. A failure in one collector is recorded in
`manifest.json["errors"]` and does not prevent other collectors from running or
mask the original test failure. `collect_on_failure` never raises.

## Configuration

- `results_dir` resolution: `context.config.userdata["results_dir"]` →
  `TESTSUITE_RESULTS_DIR` environment variable → `/tmp/results`.
- `KDE_FAILLOG_JOURNAL_LINES` caps `journalctl` output (default `2000`).
- `KDE_FAILLOG_COREDUMP_LINES` caps `coredumpctl list` output (default `100`).

## Future work

- `WAYLAND_DEBUG` ring buffer capture is not implemented in this PR.

## Usage in an environment hook

```python
from tests.shared.kde_faillog import collect_on_failure

def after_scenario(context, scenario):
    collect_on_failure(context, scenario)
```

---
name: kde-dbus-control-plane
description: "Exact D-Bus service/path/interface names for KDE PlasmaShell and KWin scripting, plus the control-plane scope rule."
metadata:
  type: reference
  audience: agents
  maturity: stable
---

# KDE D-Bus Control Plane

## Scope Rule

`org.kde.PlasmaShell.evaluateScript` and `org.kde.kwin.Scripting` are for **diagnostics,
state inspection, layout dumps, and between-scenario session reset only**.

They must **never** be the primary way a test interacts with the desktop. Real users do not
drive Plasma through `evaluateScript`; a test that opens Kickoff or changes a setting through
it validates a debugging path that ships to nobody and would pass while the real UI is broken.
Actual user interaction belongs in the AT-SPI/WebDriver layer or app-specific CLI/D-Bus entry
points (`kcmshell6`, KRunner, desktop-file activation).

## PlasmaShell

- **Service:** `org.kde.plasmashell`
- **Object path:** `/PlasmaShell`
- **Interface:** `org.kde.PlasmaShell`
- **Upstream source:** `plasma-workspace/shell/dbus/org.kde.PlasmaShell.xml`

### Methods

| Method | Signature | Use in tests |
|---|---|---|
| `evaluateScript(QString script)` | `s` | Diagnostics, reset, invariant probes only. |
| `dumpCurrentLayoutJS()` | returns `QString` | Golden-snapshot source for the live panel/widget layout. |
| `grabContainmentImage(QString name, int width, int height, QString targetPath)` | `s i i s` | Screenshot capture of a containment. |
| `activateLauncherMenu()` | — | **Do not use in tests** — belongs in AT-SPI/WebDriver. |
| `setWallpaper(QString wallpaperPlugin, QVariantMap parameters, uint screenNum)` | `s a{sv} u` | **Do not use in tests** — belongs in System Settings / AT-SPI. |

### Gating

`evaluateScript` is refused when **either** condition holds:

1. `immutability() == Plasma::Types::SystemImmutable` — the desktop is system-immutable
   ("Widgets are locked").
2. `!KAuthorized::authorize("plasma-desktop/scripting_console")` — policy denies the
   scripting console.

Both permit by default on a normal desktop. Hardened or kiosk variants will refuse.

`tests/shared/kde_shell_steps.py` raises `PlasmaScriptingDisabledError` for these refusals;
callers can turn it into a scenario skip.

## KWin Scripting

- **Service:** `org.kde.KWin`
- **Object path:** `/Scripting`
- **Interface:** `org.kde.kwin.Scripting`
- **Upstream source:** `kwin/src/scripting/scripting.h`

### Methods

| Method | Signature | Use in tests |
|---|---|---|
| `loadScript(QString filePath, QString pluginName)` | `s s` → `int` | Load a temp JS file; returns script ID. |
| `loadDeclarativeScript(QString filePath, QString pluginName)` | `s s` | Not currently used by the suite. |
| `isScriptLoaded(QString pluginName)` | `s` → `boolean` | Poll until the script finishes. |
| `unloadScript(QString pluginName)` | `s` | Always run in `finally` to avoid leaks. |
| `start()` | — | Start loaded scripts. |

### Workspace API inside a script

- `workspace.windowList()` — array of all managed client windows.
- `workspace.activeWindow` — currently focused window object.
- `workspace.showDebugConsole()` — opens the KWin interactive debug console.

Scripts cannot write files directly; they emit results via `print()`, which lands in the
systemd user journal tagged with `js:`. `kwin_script()` captures and filters this output.

## KWin Diagnostics

- **Service:** `org.kde.KWin`
- **Object path:** `/KWin`
- **Interface:** `org.kde.KWin`
- **Upstream source:** `kwin/src/dbusinterface.{h,cpp}`

### Methods

| Method | Signature | Use in tests |
|---|---|---|
| `supportInformation()` | returns `QString` | Failure diagnostics — full graphics/protocol/composite log. |
| `currentDesktop()` | → `int` | Virtual desktop queries. |
| `setCurrentDesktop(int desktop)` | `i` | Session reset only, never primary interaction. |
| `activeOutputName()` | → `QString` | Output diagnostics. |

## Invocation

Inside the Argo runner container, gdbus calls are forwarded over SSH to the VM because the
systemd user bus rejects cgroup-external connections. The SSH command sources
`/tmp/session.env` first so the D-Bus session bus address is available:

```bash
source /tmp/session.env 2>/dev/null; gdbus call --session --dest org.kde.plasmashell --object-path /PlasmaShell --method org.kde.PlasmaShell.evaluateScript '...'
```

Locally (e.g. a developer workstation with a live Plasma session), gdbus is called directly.

## Capability Probes

Use `org.freedesktop.DBus.Introspectable.Introspect` against the service/object path:

```bash
gdbus introspect --session --dest org.kde.plasmashell --object-path /PlasmaShell
gdbus introspect --session --dest org.kde.KWin --object-path /KWin
```

`plasma_available(context)` and `kwin_available(context)` wrap these and return booleans for
skip decisions.

---
name: qecore-headless-restarts-gdm-bus-socket-churn
description: "Why session-readiness checks must re-resolve the D-Bus address: qecore-headless restarts GDM and replaces the session bus socket."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# qecore-headless restarts GDM — the session bus socket is replaced

**Symptom:** the lane provisions fully (nested target ready, test user created, GDM started, Wayland session up, qecore headless installed) and then `tests/shared/wait_for_shell.py` fails with this exact progression:

```
attempts 1–14 : ServiceUnknown
attempts 15–30: Could not connect: No such file or directory
```

**Cause:** `qecore-headless` **restarts GDM**. The outgoing session's D-Bus/AT-SPI socket (`$XDG_RUNTIME_DIR/bus`) is destroyed and a new autologin session publishes a new one. The two error strings are two phases of the same restart, and both are retryable:

| Error | Meaning | Retryable? |
|---|---|---|
| `ServiceUnknown` | bus is alive, `org.gnome.Shell` has not taken its name yet | yes |
| `Could not connect: No such file or directory` | the bus **socket** is gone — GDM is mid-restart | yes |

**Rules for any session-readiness helper:**

1. Treat `ServiceUnknown` *and* connection/socket errors (`No such file or directory`, `ENOENT`, connection refused) as retryable. Neither is terminal.
2. **Re-resolve the session bus address on every attempt.** A connection or `DBUS_SESSION_BUS_ADDRESS` cached before the restart points at a destroyed socket and can never recover. Re-read `DBUS_SESSION_BUS_ADDRESS` / `XDG_RUNTIME_DIR` and fall back to `/run/user/<uid>/bus` each time.
3. **Never *unset* `DBUS_SESSION_BUS_ADDRESS` while the socket is missing.** With no address, `gdbus` falls back to `dbus-launch --autolaunch`, which fails with `Error connecting: Error spawning command line "dbus-launch --autolaunch=..."` (or worse, spawns a private bus the real session never joins). Observed in lab run `testsuite-727-...-bmlwm`. Keep the canonical `unix:path=$XDG_RUNTIME_DIR/bus` so the next poll connects the instant the replacement session creates it.
4. Require **stable** readiness (two consecutive good checks) so you do not latch onto the outgoing session microseconds before GDM tears it down.
5. Budget a wall-clock deadline that covers a whole restart cycle (300s), polled — not a bare `sleep` and not a short fixed attempt count.

## Distinguishing "helper is wrong" from "the session never came back"

`gdbus`'s error text tells you which side is at fault:

| gdbus error | What it means |
|---|---|
| `Could not connect: No such file or directory` | address IS set, socket absent — GDM restart in progress (or the session never returned) |
| `Error spawning command line "dbus-launch --autolaunch=..."` | address is **unset/empty** — GIO fell back to autolaunch. This can never work in the test container (no X11, `--close-stderr` hides the reason). A readiness helper that produces this has a bug in its env handling. |

`wait_for_shell()` therefore (a) always sets a non-empty `DBUS_SESSION_BUS_ADDRESS`, (b) short-circuits before spawning `gdbus` when the socket file is absent, and (c) prints a `collect_session_diagnostics()` snapshot — socket presence, `ls -la` of the runtime dir, `loginctl list-sessions`, `systemctl status gdm` — on the first failure, every 15th failure, and once at timeout.

**Read the snapshot before touching this repo:** if the socket never appears and `loginctl` shows no user session for uid 1000 for the whole budget, the replacement autologin session never came back. That is a lane/GDM provisioning problem in `<image-org>/lab` (`run-container-tests.yaml`), not a testsuite bug — no amount of polling in `wait_for_shell.py` can fix it.

## Confirmed outcome (lab run `testsuite-737-...-5mlvl`, 2026-08-07)

With the diagnostics in place, both lanes produced this at timeout:

```
ERROR: GNOME Shell readiness failed after 151 attempts / 300.2s (budget 300s).
Error classes: bus-unavailable=137, service-unknown=14.
Last error: session bus socket /run/user/1000/bus does not exist
Final session diagnostics:
  socket /run/user/1000/bus exists=False
  ls -la runtime dir: ls: cannot access '/run/user/1000': No such file or directory
  loginctl list-sessions: No sessions.
  systemctl status gdm: Active: active (running)
```

`gdm.service` is healthy, but the whole runtime dir for uid 1000 is gone and `loginctl` cycles **greeter-only** sessions (`gdm-greeter` / `gdm-greeter-2`, uids 60578–60582) — a uid-1000 `bluefin-test` session is never recreated. GDM comes back to the **greeter**, not to autologin.

So the post-restart failure is the [GDM autologin](gdm-autologin.md) failure mode, one restart later: no autologin ⇒ no user session ⇒ no `/run/user/1000` ⇒ no bus, permanently. **No amount of polling in `wait_for_shell.py` can fix this**; the fix belongs to the lane that restarts GDM (`run-container-tests.yaml` in the lab repo), which must ensure autologin survives the `qecore-headless` restart.

**Ruled out, do not re-investigate:** Argo semaphore/concurrency (a solo run failed identically) and "just wait for the session to settle" (the settle probe passed the check and then the socket died immediately after).

---

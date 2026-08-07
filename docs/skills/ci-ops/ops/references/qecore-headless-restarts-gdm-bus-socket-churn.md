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
3. Require **stable** readiness (two consecutive good checks) so you do not latch onto the outgoing session microseconds before GDM tears it down.
4. Budget a wall-clock deadline that covers a whole restart cycle (300s), polled — not a bare `sleep` and not a short fixed attempt count.

**Ruled out, do not re-investigate:** Argo semaphore/concurrency (a solo run failed identically) and "just wait for the session to settle" (the settle probe passed the check and then the socket died immediately after).

---

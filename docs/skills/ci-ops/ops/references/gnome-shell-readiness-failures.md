---
name: gnome-shell-readiness-failures
description: "Deep dive: GNOME Shell readiness failures in container-QA lanes"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# GNOME Shell readiness failures in container-QA lanes

`tests/shared/wait_for_shell.py` gates every GNOME lane. When it fails, the
error class in the log identifies the layer at fault. Read the class before
changing anything.

## Read the diagnostics snapshot first

`collect_session_diagnostics()` fires on the first failure, every 15th, and at
timeout. It reports the bus address, `XDG_RUNTIME_DIR`, whether the socket
exists, a listing of the runtime dir, `loginctl list-sessions`, and
`systemctl status gdm`. Diagnose from that snapshot rather than reconstructing
state by hand.

## Error classes

| Class | Meaning | Owner |
|---|---|---|
| `bus-unavailable` | `/run/user/1000/bus` does not exist | Lab — no user session registered |
| `service-unknown` | Bus reachable, `org.gnome.Shell` not yet on it | Usually transient; persistent means the shell never started |
| `shell-not-ready` | Shell present, `Shell.Eval` not answering correctly | Check `--unsafe-mode` is in effect |

A `dbus-launch --autolaunch` error means `DBUS_SESSION_BUS_ADDRESS` was empty:
GIO only autolaunches then. The helper now refuses to reach that path, so if it
reappears it is a new fault.

## Decision rule

If the socket never appears **and** `loginctl` lists no uid-1000 session, stop.
The fault is in the lane, not in this helper. Fix it in the infrastructure repo.

## The host GPU is exclusive and is not a per-lane resource

Nothing in a nested QA target may take DRM master. mutter's native backend
claims `/dev/dri/card*` exclusively, so on a single-GPU node only the first
lane can start a session. Every other lane logs:

```
gnome-shell: Failed to open gpu '/dev/dri/card1': GDBus.Error:System.Error.EBUSY: Device or resource busy
gnome-shell: Failed to make thread 'KMS thread' high priority scheduled: Timeout was reached
gdm: GdmDisplay: Session never registered, failing
gdm: GdmLocalDisplayFactory: maximum number of display failures reached. Giving up.
```

Because every *display* dies, GDM churns greeter sessions and never recreates
the uid-1000 session. That greeter churn is login-loop protection — it is
**not** evidence of a broken autologin config, and `/etc/gdm/custom.conf`
remains intact throughout. Chasing autologin here wastes time.

The cure is to force every shell instance into mutter's headless backend with a
virtual monitor, so no lane claims DRM master. Lingering the test user is
hardening only: with the GPU contended it merely shifts the failure class from
`bus-unavailable` to `service-unknown`, because the shell still never starts.

## Never fix this by widening a timing window

Raising the readiness budget cannot help when the socket is absent for the
entire run. Treat a flat, unchanging error class across hundreds of attempts as
proof that something is permanently missing, not slow.

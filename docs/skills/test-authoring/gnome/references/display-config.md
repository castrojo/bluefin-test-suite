---
name: display-config
description: "MIME, display, and session configuration in containerized tests."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Display Config

## xdg-mime in container mode

`_xdg_mime_default(mime_type)` in smoke steps.py runs `xdg-mime query default`
to check MIME handler registration. When `_IN_CONTAINER` is True (runner
container SSHing into the VM), `xdg-mime` is not installed on the container
host — it lives in the Bluefin VM. Always route through `_ssh_run` in that
case.

**Critical**: SSH sessions do NOT inherit the GNOME user session `XDG_DATA_DIRS`.
Flatpak apps (Firefox, Papers, Loupe, Showtime) register MIME handlers under
`/var/lib/flatpak/exports/share/applications/`. Without this path in
`XDG_DATA_DIRS`, `xdg-mime query default` returns empty for Flatpak MIME types.

**Keep allowlists synced to the OOTB set**: the `DOCUMENT_VIEWERS` /
`IMAGE_VIEWERS` / `TEXT_EDITORS` / `VIDEO_PLAYERS` sets in smoke `steps.py`
must match what `flatpak_permissions.feature` says the image actually ships.
Bluefin ships `org.gnome.Showtime` as its OOTB video player — a stale
allowlist (e.g. Celluloid-only) blocks the matching mimeapps.list default in
<image-org>/common from ever passing.

Always set `XDG_DATA_DIRS` explicitly in the SSH call:

```python
from app_support import _IN_CONTAINER, _ssh_run
if _IN_CONTAINER:
    result = _ssh_run(
        "XDG_DATA_DIRS=/var/lib/flatpak/exports/share"
        ":/home/bluefin-test/.local/share/flatpak/exports/share"
        ":/usr/local/share:/usr/share "
        f"xdg-mime query default {mime_type}"
    )
    return result.stdout.strip()
```

`xdg-mime query default` does NOT require a running D-Bus session.

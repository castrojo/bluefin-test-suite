---
name: bazzite-extension-state-use-getextensioninfo-not-shell-eval
description: "Deep dive: Bazzite extension state: use GetExtensionInfo, not Shell.Eval"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## Bazzite extension state: use GetExtensionInfo, not Shell.Eval

`Shell.Eval` + `Main.extensionManager.lookup(uuid)?.state` is unreliable on GNOME 50 (Bazzite). Use the stable D-Bus method:

```python
import subprocess, re

def _extension_state(context, uuid: str) -> str:
    result = subprocess.run(
        ['gdbus', 'call', '--session',
         '--dest', 'org.gnome.Shell',
         '--object-path', '/org/gnome/Shell/Extensions',
         '--method', 'org.gnome.Shell.Extensions.GetExtensionInfo',
         f"'{uuid}'"],   # GVariant string — single quotes required
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        return "99"
    m = re.search(r"'state':\s*<uint32\s+(\d+)>", result.stdout)
    return m.group(1) if m else "99"
```

**CRITICAL — GVariant quoting:** UUIDs like `logomenu@aryan_k` contain `@` which is invalid bare GVariant. Always wrap in single quotes: `f"'{uuid}'"`.

Extension state values:

| State | Meaning |
|---|---|
| 1 | ENABLED |
| 2 | DISABLED |
| 3 | ERROR |
| 6 | INITIALIZED (transient — poll through) |
| 99 | UNINSTALLED / call failed |

Poll through states 6 and 8 with a timeout — Bazzite's 11 extensions can take up to 90 seconds to fully activate.

---

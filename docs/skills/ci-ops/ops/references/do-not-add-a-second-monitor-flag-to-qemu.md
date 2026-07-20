---
name: do-not-add-a-second-monitor-flag-to-qemu
description: "Deep dive: Do not add a second -monitor flag to QEMU"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Do Not Add A Second Monitor Flag To Qemu

## Do not add a second -monitor flag to QEMU

`e2e.yml` opens a QEMU monitor unix socket at boot:
```
-monitor unix:/tmp/qemu-monitor.sock,server,nowait
```
`tests/shared/qemu_screendump.py` uses this socket for fallback screenshots. A second `-monitor` flag competes for VM state. To capture the framebuffer from a custom step:
```bash
sudo python3 tests/shared/qemu_screendump.py results/my-screenshot.png
```

---

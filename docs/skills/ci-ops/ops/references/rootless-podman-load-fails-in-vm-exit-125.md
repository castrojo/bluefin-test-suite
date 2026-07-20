---
name: rootless-podman-load-fails-in-vm-exit-125
description: "Deep dive: Rootless podman load fails in VM (exit 125)"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Rootless Podman Load Fails In Vm Exit 125

## Rootless podman load fails in VM (exit 125)

**Symptom:** "Load runner container into VM" step exits 125 with:
```
lchown /var/spool/mail: invalid argument
potentially insufficient UIDs or GIDs available in user namespace
```

**Cause:** `fedora-minimal` has a layer that sets `/var/spool/mail` to `root:mail`. Rootless podman needs subuid/subgid mappings for the test user.

**Fix (in e2e.yml):** Before `podman load`:
```bash
ssh ${SSH_COMMON} -p 2222 bluefin-test@127.0.0.1 \
  "sudo bash -c 'grep -q bluefin-test /etc/subuid || echo \"bluefin-test:100000:65536\" >> /etc/subuid; \
   grep -q bluefin-test /etc/subgid || echo \"bluefin-test:100000:65536\" >> /etc/subgid'"
ssh ${SSH_COMMON} -p 2222 bluefin-test@127.0.0.1 podman system migrate 2>/dev/null || true
```

Do NOT switch to `sudo podman load` — that puts the image in root storage, but all `podman run` calls in the VM run as `bluefin-test`.

---

---
name: fedora-version-targets
description: "Deep dive: Fedora version targets"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## Fedora version targets

Three Fedora versions appear in this repo. They are not interchangeable.

| Context | Fedora version | Why |
|---|---|---|
| **`behave --dry-run` CI container** (`pr-validate.yml`) | `fedora:41` (pinned digest) | qecore/dogtail/GObject ABI target; PyGObject from Ubuntu breaks |
| **Test runner image** (`container/Containerfile.runner`) | `fedora-minimal:latest` (rebuilt weekly) | Base for the runner container shipped to the VM |
| **OS under test (gnomeos)** | `gnomeos-latest` (≈ Fedora 44 / GNOME 50) | `quay.io/gnome_infrastructure/gnome-build-meta` |
| **OS under test (Bluefin)** | Fedora 41 based (stable/gts/lts) | Do NOT test against F42 — Bluefin does not ship it |

**Never use F42**: no Bluefin or Bazzite image is based on Fedora 42.

---

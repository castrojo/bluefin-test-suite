---
name: composefs-file-capability-regression
description: "Deep dive: composefs file-capability regression"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Composefs File Capability Regression

## composefs file-capability regression

A `@health @composefs @regression` scenario in `system_health.feature` checks
that `newuidmap` and `newgidmap` retain their `security.capability` xattrs
after a composefs-backed ostree deployment.

**Root cause:** `buildah commit` (without `--squash`) produces a multi-layer OCI image. The composefs xattr injection expects a flat single-layer input; multi-layer output silently strips `security.capability` xattrs. Fix: `podman build --squash-all` in the export recipe.

If `getcap` returns no capabilities for these binaries, the image build
pipeline produced a multi-layer OCI artifact. File the regression against the
image build repo, not the test suite.

`ping` is intentionally not asserted: Fedora's iputils ships `/usr/bin/ping`
with no file capability (plain 0755; only `clockdiff`/`arping` get
`%caps(cap_net_raw=p)`) and provides unprivileged ping via
`net.ipv4.ping_group_range` instead. A `cap_net_raw` assertion can never hold
on a Fedora-based image (see projectbluefin/bluefin#989), so checking it only
produced a deterministic false failure, never a regression signal.
---

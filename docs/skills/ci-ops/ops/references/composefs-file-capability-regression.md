---
name: composefs-file-capability-regression
description: "Deep dive: composefs file-capability regression"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## composefs file-capability regression

A `@health @composefs @regression` scenario in `system_health.feature` checks
that `newuidmap`, `newgidmap`, and `ping` retain their `security.capability`
xattrs after a composefs-backed ostree deployment.

**Root cause:** `buildah commit` (without `--squash`) produces a multi-layer OCI image. The composefs xattr injection expects a flat single-layer input; multi-layer output silently strips `security.capability` xattrs. Fix: `podman build --squash-all` in the export recipe.

If `getcap` returns no capabilities for these binaries, the image build
pipeline produced a multi-layer OCI artifact. File the regression against the
image build repo, not the test suite.
---

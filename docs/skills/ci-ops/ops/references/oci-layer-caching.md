---
name: oci-layer-caching
description: "Deep dive: OCI layer caching"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Oci Layer Caching

## OCI layer caching

Podman layers are cached at `/var/lib/containers/storage`, keyed by the resolved image digest.

- A cache hit skips the pull entirely; repeat runs drop from roughly 5-15 minutes to about 30 seconds for this stage.
- The cache invalidates automatically when the image digest changes.
- If you see digest-resolution failures in CI (for example `skopeo inspect` or manifest-inspect output), that is the cache-key resolution step — verify the image exists and is publicly accessible.

---

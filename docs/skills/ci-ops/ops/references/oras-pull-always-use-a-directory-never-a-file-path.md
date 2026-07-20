---
name: oras-pull-always-use-a-directory-never-a-file-path
description: "Deep dive: oras pull: always use a directory, never a file path"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Oras Pull Always Use A Directory Never A File Path

## oras pull: always use a directory, never a file path

`oras pull <ref> --output <path>` (or `-o <path>`) expects a **directory**. Passing a file path creates a directory with that name and puts the artifact inside it.

```bash
oras pull "${REGISTRY}:smoke-latest" --output scratch/smoke.png

mkdir -p scratch/smoke
oras pull "${REGISTRY}:smoke-latest" -o scratch/smoke/
SHOT=$(find scratch/smoke/ -name "*.png" | head -1)
cp "$SHOT" screenshots/target.png
```

The artifact filename inside the OCI artifact is `desktop-screenshot.png` (set at push time with `oras push ... desktop-screenshot.png:image/png`).

---

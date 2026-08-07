---
name: cross-image-tag-skipping-bluefin-on-non-bluefin-images
description: "Deep dive: Cross-image tag skipping: @bluefin on non-bluefin images"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Cross Image Tag Skipping Bluefin On Non Bluefin Images

## Cross-image tag skipping: @bluefin on non-bluefin images

The common suite skips scenarios tagged `@bluefin` when `IMAGE` env var refers to a
non-bluefin image (e.g. dakota). This is implemented via `_is_bluefin_image()` in
`tests/common/features/environment.py`.

**Pitfall**: match the image *name*, not the full URL. The org name `projectbluefin`
contains `"bluefin"`, so naively checking `"bluefin" in image_url.lower()` returns
`True` for `ghcr.io/projectbluefin/dakota:testing`.

Correct pattern:

```python
def _is_bluefin_image(image: str) -> bool:
    lower = image.lower()
    name = lower.split("/")[-1].split(":")[0].split("@")[0]
    return "bluefin" in name or "bazzite" in lower
```

This extracts the image name component (`bluefin`, `dakota`, etc.) before checking.

The smoke suite environment replicates this same pattern so `@bluefin` tags are
respected in AT-SPI tests as well.

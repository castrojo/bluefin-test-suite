---
name: common-shell-tools-missing-on-bluefin-lts-bluefin-gdx
description: "Deep dive: common shell tools missing on bluefin:lts / bluefin-gdx"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## common shell tools missing on bluefin:lts / bluefin-gdx

**Symptom:** `common` suite: 7 failures — `zsh`, `fish`, `bat`, `eza`, `fd`, `ripgrep`, `starship` not found.

**Cause:** `LockLayering=true` prevents `rpm-ostree install --apply-live`. `brew-setup.service` is masked in CI.

**Status:** Image quality issue — tests correctly detect missing tools. Report to image maintainers. If tools are not expected on an image, add `@requires_brew` tag to scenarios in `common_shell.feature`.

---

---
name: oneshot-systemd-service-state-use-result-not-activestate
description: "Deep dive: Oneshot systemd service state — use Result, not ActiveState"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Oneshot Systemd Service State Use Result Not Activestate

## Oneshot systemd service state — use Result, not ActiveState

**Symptom:** `common_services.feature` scenarios fail with output `inactive` when
checking `ActiveState --value` even though the service ran successfully.

**Cause:** Oneshot services transition to `ActiveState=inactive` (dead) after they
finish — this is correct behaviour, not a failure. Asserting `active` always fails
for completed oneshot units.

**Fix:** Check `Result --value` instead. A successfully completed oneshot reports
`Result=success`:

```bash
systemctl show ublue-system-setup.service --property=Result --value
```

Affected services: `rechunker-group-fix.service`, `ublue-system-setup.service`,
`ublue-user-setup.service` (--user), `dconf-update.service`,
`bootc-unified-storage.service`.

See `docs/skills/test-authoring/behave/SKILL.md` "Shared SSH helpers" section for the feature-file pattern.

**Exception:** Services that are masked in CI (`flatpak-preinstall.service`,
`flatpak-nuke-fedora.service`) will have `Result=exit-code` or no result at all.
Keep those quarantined until the masking is removed at the image level.

---

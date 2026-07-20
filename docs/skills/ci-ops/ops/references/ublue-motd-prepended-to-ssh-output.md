---
name: ublue-motd-prepended-to-ssh-output
description: "Deep dive: ublue-motd prepended to SSH output"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Ublue Motd Prepended To Ssh Output

## ublue-motd prepended to SSH output

**Symptom:** SSH assertions fail — step expects `stdout == "ok"` but gets `"Welcome to Bluefin...\nok"`.

**Cause:** Some images ship `/etc/profile.d/ublue-motd.sh` which prints a MOTD in login shells.

**Fix (in e2e.yml VM setup):**
```bash
sudo touch "${VAR}/home/bluefin-test/.config/no-show-user-motd"
```

`ssh_steps.py` checks the **last line** of stdout (not the whole output) as a defensive measure. Do not change assertions to substring-match — the last-line approach is more robust.

---

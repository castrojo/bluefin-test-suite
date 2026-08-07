---
name: common-suite-execution-model-runner-container-not-inside-vm
description: "Deep dive: common suite execution model — runner container, not inside VM"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Common Suite Execution Model Runner Container Not Inside Vm

## common suite execution model — runner container, not inside VM

**The common suite is an SSH-driven black-box tester.** It runs FROM the Argo runner
container (fedora:latest) and SSHes INTO the VM. It is NOT an AT-SPI suite and does not
require qecore-headless or a display.

**Environment variables required in the runner container:**
- `VM_IP` — IP of the Bluefin VM (set by run-gnome-tests.yaml automatically)
- `VM_USER` — SSH user (default: `bluefin-test`)
- `SSH_KEY` — path to the private key, e.g. `/etc/ssh/test-key/id_ed25519`

**Root cause of "Cannot reach VM at  over SSH after 5 attempts":**
The common suite's `environment.py` reads `VM_IP` from env. If behave runs inside
the VM via qecore-headless (old bug), `VM_IP` is empty and every SSH step fails.

**Fix (applied in `projectbluefin/lab` `a70e1c4`):** `run-gnome-tests.yaml` now has a dedicated
`elif [[ "${SUITE}" == "common" ]]` branch that:
1. Installs behave in the runner container if absent
2. Exports `VM_IP`, `VM_USER`, `SSH_KEY`
3. Runs `python3 -m behave /workspace/bluefin-test-suite/tests/common/features/`
4. Writes results.json locally (skips the VM→runner SCP step)

Do NOT add common to the qecore-headless path. Common has no GNOME AT-SPI dependency.

---

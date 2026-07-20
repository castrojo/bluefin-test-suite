---
name: stdin-heredoc-consumption-bug-in-run-gnome-tests-yaml
description: "Deep dive: Stdin Heredoc Consumption bug in run-gnome-tests.yaml"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## Stdin Heredoc Consumption bug in run-gnome-tests.yaml

**Symptom:** The `run-gnome-tests` step in `bluefin-qa-pipeline` completes instantly with exit status 0 but runs no behave tests inside the VM, only printing `root-ssh-diag-ready`.

**Cause:** The runner script executes inside a bash heredoc (`exec bash <<'SCRIPT_EOF'`). Nested commands like `ssh` read from standard input by default, consuming the rest of the heredoc. This causes bash to see EOF and exit prematurely with exit status 0 (last successful command's exit code).

**Fix:** Wrap the entire heredoc script block (or any nested ssh/scp commands) in a block with stdin redirected from `/dev/null`:
```bash
exec bash <<'SCRIPT_EOF'
{
  set -euo pipefail
  # ... script logic ...
} < /dev/null
SCRIPT_EOF
```
This isolates standard input, preventing nested `ssh`/`scp` calls from consuming the SCRIPT_EOF script block.

---

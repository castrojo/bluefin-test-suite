---
name: yaml-orphan-keys-in-e2e-yml
description: "Deep dive: YAML orphan keys in e2e.yml"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## YAML orphan keys in e2e.yml

**Symptom:** PRs fail merge queue validation with `{"total_count":0,"jobs":[]}`.

**Cause:** A step block missing its `- name:` header has its `if:`, `id:`, and `run:` keys treated as orphan keys on the prior step. `yaml.safe_load` silently uses last-wins; GHA schema checker rejects it.

**How to spot:** Visually scan for any `if:` / `id:` / `run:` at the 8-space indent level without a preceding `- name:` on the same level. `yaml.safe_load` will not catch this.

Always add `      - name: My Step Name` before each step's body.

---

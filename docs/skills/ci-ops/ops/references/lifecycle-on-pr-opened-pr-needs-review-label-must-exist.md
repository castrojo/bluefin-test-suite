---
name: lifecycle-on-pr-opened-pr-needs-review-label-must-exist
description: "Deep dive: lifecycle / on-pr-opened: pr/needs-review label must exist"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Lifecycle On Pr Opened Pr Needs Review Label Must Exist

## lifecycle / on-pr-opened: pr/needs-review label must exist

**Symptom:** Every new PR fails `lifecycle / on-pr-opened` with `'pr/needs-review' not found`.

**Cause:** The `<image-org>/common` lifecycle workflow labels new PRs with `pr/needs-review`. If the label doesn't exist, `gh pr edit --add-label` exits 1.

**Fix:** Ensure the label exists in the repo:
```bash
gh label create "pr/needs-review" --repo <image-org>/testsuite \
  --color "#0075ca" --description "Needs review from a maintainer"
```

Do not delete this label.

---

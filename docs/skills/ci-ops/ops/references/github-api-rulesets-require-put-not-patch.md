---
name: github-api-rulesets-require-put-not-patch
description: "Deep dive: GitHub API: rulesets require PUT not PATCH"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Github Api Rulesets Require Put Not Patch

## GitHub API: rulesets require PUT not PATCH

`PATCH /repos/{owner}/{repo}/rulesets/{id}` returns 404 even with `repo` scope and admin access.

Use `PUT` with the **full** ruleset body (including `name`, `enforcement`, `conditions`, `bypass_actors`, and all `rules`):

```bash
gh api --method PUT repos/projectbluefin/bluefin/rulesets/17070404 \
  --input /tmp/full-ruleset.json \
  --jq '.rules[] | select(.type=="pull_request") | .parameters.required_approving_review_count'
```

To get the current body for editing:
```bash
gh api repos/projectbluefin/bluefin/rulesets/17070404 \
  | jq '{name, enforcement, conditions, bypass_actors, rules}' > /tmp/ruleset.json
```

---

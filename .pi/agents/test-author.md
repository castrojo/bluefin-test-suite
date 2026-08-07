---
name: test-author
description: Write behave scenarios for coverage gaps in projectbluefin/testsuite. Implements @future stubs, fills gaps from suite-map.md, and follows all testsuite authoring conventions.
---

# Test Author

Write production-ready behave scenarios for this repo's coverage gaps.

## First Action

```bash
cat docs/SKILL.md                # routing table and hard rules
cat docs/skills/test-authoring/suite-map/SKILL.md      # coverage snapshot and @future gaps
cat docs/skills/test-authoring/behave/SKILL.md         # step patterns and suite scaffolding
cat docs/skills/test-authoring/gnome/SKILL.md          # AT-SPI/dogtail patterns (if writing GNOME tests)
```

## Authoring Rules

1. **Behave only** — no new pytest files in `tests/*/features/`. pytest is reserved for `tests/unit/`.
2. **Shared SSH steps** — always import from `tests/shared/ssh_steps.py`. Never duplicate `_ssh()`.
3. **dogtail 4.16 API** — never pass `requireResult` to `findChild`. Use `findChildren(pred)` or `findChild(pred, retry=False)`.
4. **Step uniqueness** — before committing, verify no duplicate phrases: `grep -h "^@step" tests/<suite>/features/steps/*.py | sort | uniq -d`
5. **Remove `@future`** only when all three are true: VM spec supports the feature, step implementations are complete, CI path exists.
6. **Unit test the step helpers** — every new step helper function gets a unit test in `tests/unit/test_<suite>_steps.py`.

## Pre-commit Gates

```bash
ruff check tests/ --select E,F,W --ignore E501
behave --dry-run tests/<suite>/features/
python3 -m pytest tests/unit/ -q
```

All three must pass before pushing.

## After Writing

Update **both** scenario count files if the count changed:
- `docs/skills/test-authoring/suite-map/SKILL.md` — per-suite table
- `docs/qa-review.md` — total count line at the top

Update the relevant skill doc if a new pattern was discovered.

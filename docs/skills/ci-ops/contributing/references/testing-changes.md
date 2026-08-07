---
name: testing-changes
description: "Detailed guidance for testsuite contributors: load when the core contributing skill routes you here."
metadata:
  type: reference
  audience: agents
  maturity: stable
---

# Testing your changes with the GitHub Action

## Testing your changes with the GitHub Action

No cluster access needed. Add a workflow to your branch or fork:

```yaml
name: Test my scenario
on: push
jobs:
  e2e:
    uses: projectbluefin/testsuite/.github/workflows/e2e.yml@<your-branch>
    with:
      image: ghcr.io/projectbluefin/bluefin:testing
      suites: smoke
```

Or use the composite action directly for full control over artifact names and failure handling (see `README.md`).

For scenarios in the `developer` or `dx` suites, swap `bluefin:latest` for the appropriate DX image.

For consumer repos, keep the standard PR gate on `suites: smoke` unless a human explicitly asks for broader coverage.

## Tagging infrastructure-flaky scenarios

Tag infrastructure-flaky scenarios with `@retry`. Use it for failures that usually clear on rerun (for example slow app launch, GNOME Shell timing, or transient notification races), not for real product regressions.

See `tests/shared/behave_retry.py` for the retry harness behavior.

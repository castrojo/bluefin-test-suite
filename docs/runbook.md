# testsuite runbook

Operational commands for `<image-org>/testsuite`. Authoring patterns and skill docs live in `docs/skills/` — load from there.

## Ownership boundary

| Area | Owner |
|---|---|
| Test suites (`tests/**`), step definitions, shared helpers | testsuite |
| Workflow templates, manifests, persistent VMs, CronWorkflows, host operations | testing-lab |

If a change touches both repos, split into two PRs.

## Local commands

```bash
# List @future / not-yet-implemented scenarios
just list-stubs

# Lint
ruff check tests/ --select E,F,W --ignore E501

# BDD dry-run for a suite
behave --dry-run tests/<suite>/features

# Unit tests
python3 -m pytest tests/unit/ -q
```

## Manual CI runs

Use `.github/workflows/manual.yml` for ad hoc image and suite runs on GitHub Actions.

```bash
# Smoke suite (auto-shards into smoke-a + smoke-b)
gh workflow run manual.yml --repo <image-org>/testsuite --ref main \
  -f image=ghcr.io/<image-org>/bluefin:testing \
  -f suites=smoke

# Common suite (auto-shards into common-a + common-b)
gh workflow run manual.yml --repo <image-org>/testsuite --ref main \
  -f image=ghcr.io/<image-org>/bluefin:testing \
  -f suites=common

# Multiple suites
gh workflow run manual.yml --repo <image-org>/testsuite --ref main \
  -f image=ghcr.io/<image-org>/bluefin:testing \
  -f suites=smoke,common,vanilla-gnome

# Installer post-boot assertions (SSH-mode, like common/lifecycle)
gh workflow run manual.yml --repo <image-org>/testsuite --ref main \
  -f image=ghcr.io/<image-org>/bluefin:testing \
  -f suites=installer

# Manual ISO validation (smoke + unattended install)
gh workflow run iso-manual.yml --repo projectbluefin/testsuite --ref main \
  -f iso_url=https://example.invalid/candidate.iso \
  -f iso_ref=<immutable-projectbluefin-iso-sha> \
  -f variant=stable

# Check recent runs
gh run list --repo <image-org>/testsuite --workflow manual.yml --limit 5

# View a run
gh run view <RUN_ID> --repo <image-org>/testsuite

# Tail failing job logs
gh run view --job=<JOB_ID> --log-failed --repo <image-org>/testsuite
```

**Diagnosing failures** — load `docs/skills/ci-ops/ops/SKILL.md` first; the on-demand references cover the most common signatures.

## Merge queue

This repo uses a merge queue (ruleset `main — merge queue`). Enqueue with:

```bash
gh pr merge <NUMBER> --repo <image-org>/testsuite --squash --auto
```

Required checks: `Lint & syntax`, `Behave dry-run`, `pytest` — all must be green before enqueueing.

## Vanilla GNOME baseline comparison

The `vanilla-gnome` suite runs against an unmodified GNOME OS disk to establish a comparison baseline:

- **Fails on vanilla** → likely upstream GNOME issue
- **Fails on downstream image but not vanilla** → likely image-specific regression

Procedure:

1. Dispatch two manual runs and wait for completion:
   - Downstream baseline: `image=ghcr.io/<image-org>/bluefin:testing`, `suites=smoke`
   - GNOME OS baseline: `image=quay.io/gnome_infrastructure/gnome-build-meta:gnomeos-latest`, `suites=vanilla-gnome`
2. Compare overlapping scenarios between `smoke` and `vanilla-gnome`.
3. Flag regressions that fail on the downstream image but pass on vanilla.

## Scenario-count updates

When counts change, update the co-authoritative sources:

- `docs/skills/test-authoring/suite-map/SKILL.md` — per-suite table
- `docs/qa-review.md` — totals line and stub posture

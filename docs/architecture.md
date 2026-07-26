# testsuite architecture

Single source of truth for ownership boundaries, repo relationships, and where different concerns live.

## Repositories

| Repo | Owns | Consumes |
|---|---|---|
| `testsuite` (this repo) | Behave features/steps, qecore/dogtail patterns, shared SSH helpers, reusable GitHub Actions | Pinned by `testing-lab` workflows and downstream image build repos |
| `testing-lab` | VM specs, KubeVirt manifests, Argo/CronWorkflows, persistent VM lifecycle | Clones testsuite at a pinned ref |
| downstream image repos (e.g., `bluefin`, `bluefin-lts`, `dakota`) | Image definitions and build workflows | Call testsuite reusable e2e workflow as a promotion gate |

## What belongs in testsuite

| Concern | Location |
|---|---|
| Behave `.feature` files | `tests/<suite>/features/` |
| Step definitions | `tests/<suite>/features/steps/` |
| Shared steps/helpers | `tests/shared/` |
| Unit tests | `tests/unit/` |
| Reusable e2e workflow | `.github/workflows/e2e.yml` |
| Composite action | `.github/actions/gnome-e2e/` |
| Agent skill tree | `docs/skills/` |

## What belongs elsewhere

| Concern | Where |
|---|---|
| VM specs, KubeVirt resources | `testing-lab` |
| Argo WorkflowTemplates / CronWorkflows | `testing-lab` |
| Image build definitions | downstream image repos |
| Promotion / cosign / packaging logic | downstream image repos or shared actions repo |

## Pull-request split rule

A change that touches both testsuite test content and testing-lab infrastructure must be split into two PRs. This keeps reviews scoped and prevents a single PR from coupling release gates.

## Trust boundaries

- **Read-only upstream namespace** — never write (issues, PRs, comments, forks) to any read-only upstream. Read-only API calls are allowed.
- **Workflow pins** — external `uses:` references must be SHA-pinned with a version comment. Floating tags are forbidden.
- **No WIP PRs** — every open PR must be ready for merge queue.
- Keep open PRs scoped and mergeable; batch related work without an artificial per-agent cap.

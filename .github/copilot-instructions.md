# testsuite — Copilot instructions

Read [`AGENTS.md`](../AGENTS.md) first — it is the local authority for paths,
ownership, build commands, and branch targets. Then read
[`docs/SKILL.md`](../docs/SKILL.md), the task → skill router, and load only the
skills your task needs. The generated catalog is `docs/skills/index.json`.

`projectbluefin/common` is the pinned shared-contract sidecar for factory-wide
rules ([label workflow](https://github.com/projectbluefin/common/blob/main/docs/skills/label-workflow.md),
[factory onboarding](https://github.com/projectbluefin/common/blob/main/docs/skills/factory-onboarding.md),
[governance](https://github.com/projectbluefin/common/blob/main/docs/skills/governance.md)).
It never overrides local authority; local rules never override a factory-wide
contract.

Humans triage, approve, review, and merge. Agents work only on issues routed to
them by assignment or `3-clanker-queue`. Clankers only transports Hive
assignments — it is not merge authority.

**Never write to `ublue-os/*`, `projectbluefin/common`, or any KDE property.**
Read-only API calls are fine.

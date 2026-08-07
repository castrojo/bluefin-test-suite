---
name: writing-skills
version: "1.0"
last_updated: "2026-07-20"
id: writing-skills
one_line_purpose: Author or maintain a testsuite skill doc within the size and format rules.
entry_point: docs/skills/meta/writing-skills/SKILL.md
category: meta
mcp_compliance_level: partial
status: active
dependencies: []
tags: [skills, authoring, docs]
description: "How to write, split, and review docs/skills/ files in testsuite. Load when creating, editing, or deleting a skill."
metadata:
  type: meta
  audience: agents
  maturity: stable
---
# Writing skills for testsuite

## When to Use

- Creating a new skill in `docs/skills/`.
- Splitting an oversized skill into `SKILL.md` + `references/`.
- Updating a skill after discovering a new pattern or workaround.
- Proposing deletion or merge of stale skills.

## When NOT to Use

- For root `AGENTS.md` or `README.md` changes — see `meta/skill-improvement/SKILL.md` for the update trigger.
- For one-off prose that does not describe *when an agent should load it*.

## Directory and file naming

- Path: `docs/skills/<category>/<name>/SKILL.md`, where `<category>` is one of
  `ci-ops`, `test-authoring`, or `meta`.
- Directory name must equal the frontmatter `name` and `id`.
- `name`: 1–64 chars, lowercase alphanumerics and hyphens only, no leading/trailing hyphen, no consecutive hyphens.
- Optional: `references/`, `scripts/`, `assets/` inside the skill directory.

### Router and catalog exceptions

- `docs/SKILL.md` is the task router required by the factory onboarding
  contract. It carries the same front-matter schema but lives outside
  `docs/skills/`.
- `docs/skills/index.md` and `docs/skills/index.json` are **generated** by
  `scripts/generate_skill_index.py`. Never hand-edit them.

## Frontmatter schema

The schema matches `projectbluefin/common`'s catalog contract so factory tooling
can read either repo. Canonical definition: [`docs/skills/index.schema.json`](../../index.schema.json).

```yaml
---
name: example
version: "1.0"
last_updated: "2026-08-07"
id: example
one_line_purpose: Do the one thing this skill exists for.
entry_point: docs/skills/<category>/example/SKILL.md
category: ci-ops | test-authoring | meta
mcp_compliance_level: partial
status: active | deprecated | reserved
dependencies: []
tags: [one, two]
description: "When to load this skill: trigger, audience, scope."
metadata:
  type: pattern | reference | meta | manifest
  audience: agents
  maturity: stable | draft
---
```

Required fields (enforced by `scripts/validate_docs.py`):

| Field | Rule |
|---|---|
| `name` | Matches the parent directory. |
| `id` | Kebab-case; must equal `name`. |
| `version` | Quoted string, e.g. `"1.0"`. |
| `last_updated` | `YYYY-MM-DD`. |
| `one_line_purpose` | ≤120 chars; imperative; distinct from `description`. |
| `entry_point` | Repo-relative path to this file. |
| `category` | `ci-ops`, `test-authoring`, or `meta`. |
| `status` | `active`, `deprecated`, or `reserved`. |
| `tags` | Non-empty list. |
| `description` | Tells the agent *when* to load the file. |

Optional: `mcp_compliance_level`, `dependencies`, `compatibility`, `license`,
and `metadata` (repo-local taxonomy: `type`, `audience`, `maturity`).

Reference files under `references/` are not catalog entries. They may carry a
short `name` and `description` only.

After changing any front matter, regenerate the catalog:

```bash
python3 scripts/generate_skill_index.py
```

## Progressive disclosure budgets

| Layer | Max size | What it holds |
|---|---|---|
| Router (`docs/SKILL.md`) | 2,000 tokens | Hard rules + routing table |
| `SKILL.md` | 5,000 tokens | When to Use / When NOT / Core process / quick examples |
| `references/<topic>.md` | 2,000 tokens | Deep dive: API quirks, manifests, full examples |
| Scripts/assets | as needed | Loaded only when the skill instructs it |

As a rule of thumb: `SKILL.md` ≤ 500 lines; references ≤ 200 lines.
These are hard limits enforced by `scripts/validate_docs.py` in CI.

## Token rules

1. **One canonical source per fact** — link, do not copy.
2. **One H1 per file**; prefer H2; avoid H5+.
3. **H2 sections ≤ 300 tokens** — split or move to references.
4. **Prefer tables** over paragraphs for maps and checklists.
5. **No badges** in skill files.
6. **Use code blocks**, not full CI logs.
7. **Use relative links** to other skills and references.
8. **Avoid nested callouts** — if it needs a note, consider a heading.

## How to split a skill

1. Run `wc -l` and estimate tokens (bytes ÷ 4).
2. Keep **When to Use / When NOT / Core Process / Red Flags / Verification** in `SKILL.md`.
3. Move large topic clusters to `references/<topic>.md`; link from `SKILL.md`.
4. Add an **On-demand references** section in `SKILL.md` listing links.
5. Preserve old links by updating paths after the move.

## How to delete or merge a skill

- Do not delete without a redirect note in the successor skill or `docs/SKILL.md`.
- Merge only when two skills share the same trigger and audience.
- Update the `docs/SKILL.md` routing table, then run
  `python3 scripts/generate_skill_index.py` to refresh the catalog.

## Review checklist

- [ ] `name` matches the parent directory, and `id` matches `name`.
- [ ] All catalog fields present; `entry_point` matches the real path.
- [ ] `description` states *when to load*.
- [ ] `python3 scripts/generate_skill_index.py --check` passes.
- [ ] `docs/SKILL.md` routing table lists the skill.
- [ ] No duplicate H1; no H5+.
- [ ] Size budgets met.
- [ ] Project/org strings replaced with `projectbluefin` / `ublue-os` placeholders where appropriate.
- [ ] Cross-links use relative paths.

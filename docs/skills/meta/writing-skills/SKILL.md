---
name: writing-skills
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

- Path: `docs/skills/<name>/SKILL.md`.
- Directory name must equal the frontmatter `name`.
- `name`: 1–64 chars, lowercase alphanumerics and hyphens only, no leading/trailing hyphen, no consecutive hyphens.
- Optional: `references/`, `scripts/`, `assets/` inside the skill directory.

## Frontmatter schema

```yaml
---
name: example
description: "When to load this skill: trigger, audience, scope."
metadata:
  type: pattern | reference | meta | manifest
  audience: agents
  maturity: stable | draft
---
```

- `description` is required and must tell the agent when to load the file.
- `compatibility` may list env constraints (≤500 chars).
- Reference files may also include frontmatter with a short `name` and `description`.

## Progressive disclosure budgets

| Layer | Max size | What it holds |
|---|---|---|
| Manifest (`docs/skills/index.md`) | 2,000 tokens | Hard rules + routing table |
| `SKILL.md` | 5,000 tokens | When to Use / When NOT / Core process / quick examples |
| `references/<topic>.md` | 2,000 tokens | Deep dive: API quirks, manifests, full examples |
| Scripts/assets | as needed | Loaded only when the skill instructs it |

As a rule of thumb: `SKILL.md` ≤ 500 lines; references ≤ 200 lines.

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

- Do not delete without a redirect note in the successor skill or `index.md`.
- Merge only when two skills share the same trigger and audience.
- Update `docs/skills/index.md` routing table.

## Review checklist

- [ ] `name` matches the parent directory.
- [ ] `description` states *when to load*.
- [ ] No duplicate H1; no H5+.
- [ ] Size budgets met.
- [ ] Project/org strings replaced with `<image-org>` / `<readonly-upstream>` placeholders where appropriate.
- [ ] Cross-links use relative paths.

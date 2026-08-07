---
name: shared-count-docs
description: "Avoiding merge collisions on qa-review.md and suite-map/SKILL.md."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Shared Count Docs

Two files are edited by **every** PR that adds or retags scenarios:

- `docs/qa-review.md` — the mechanical recount line and stub-posture section
- `docs/skills/test-authoring/suite-map/SKILL.md` — the per-suite count matrix

`AGENTS.md` makes updating both mandatory when totals change, so they are the
repo's permanent merge-contention hotspot. Concurrent test PRs never conflict on
code — they conflict here.

## Why "MERGEABLE" is misleading

GitHub computes mergeability against the **current base**, one PR at a time. Two
PRs that each edit the recount line both report MERGEABLE while the other is
unmerged. The conflict materialises the moment the first one lands.

Never treat a green mergeable badge as proof that a batch of PRs can land in any
order. Diff the shared files across the open set before queueing:

```bash
for p in <pr numbers>; do
  echo "=== $p ==="
  gh pr diff "$p" | awk '/^diff --git/{f=/qa-review|suite-map/} f&&/^[+-][^+-]/'
done
```

## Order by blast radius, largest first

A PR that **restructures** either file (adds a column, rewrites the matrix,
replaces a section) must merge **before** PRs that only edit rows or totals.
Reversing that order forces the restructuring PR — the larger and harder one —
to be redone against the new content.

Rank the open set by how much of the shared file each one rewrites, merge the
biggest first, then rebase the rest. Rebasing a one-line count edit onto a new
table shape is trivial; rebasing a full table rewrite onto three separate row
edits is not.

## Keep count edits isolated

Put the `qa-review.md` + `suite-map/SKILL.md` updates in their **own commit**,
last in the branch. A rebase then conflicts in exactly one commit that contains
nothing but counts, instead of scattering conflicts through the code commits.

Recount mechanically rather than by arithmetic on the previous total — the
number on `main` may already be stale, and adding your delta to a wrong number
propagates the error.

## When you cannot merge

If you are not the one merging, **say so on the PR**: name which shared files it
touches, which open PR should land first, and that a rebase is required after.
An agent that opens a contending PR silently has handed the conflict to whoever
merges.

## Red flags

- Three or more open PRs whose diffs all touch the recount line
- A count total that no `behave --dry-run` output supports
- A PR marked ready that edits the suite matrix while a matrix-restructuring PR
  is open and unmerged
- Counts updated in `suite-map/SKILL.md` but not `docs/qa-review.md`, or the
  reverse

## Verification

- [ ] Both shared files updated, or neither (totals genuinely unchanged)
- [ ] Totals derived from a fresh `behave --dry-run`, not from arithmetic
- [ ] Shared-file diffs compared against every other open PR
- [ ] Count changes isolated in their own final commit
- [ ] Merge order noted on the PR when another PR must land first

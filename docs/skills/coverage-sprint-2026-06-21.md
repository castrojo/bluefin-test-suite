---
name: coverage-sprint-2026-06-21
description: "Final status report for the 2026-06-21 coverage sprint. Tracks which work items landed, which remain backlog, and the post-sprint documentation follow-up."
metadata:
  type: sprint-report
  status: completed
  owner: fleet
---

# Coverage Sprint — 2026-06-21

## Final status summary

- **Sprint status:** DONE
- **Completed PRs / sprint branches:** #472–#484
- **Post-sprint docs sweep:** DONE
- **Authoritative coverage snapshot from the queued/merged sprint heads:** 337 `Scenario:` entries across 46 feature files
- **Remaining backlog from the original plan:** bctl coverage, AI/ML stack coverage, power-management coverage

## Work item status

| Item | Status | Outcome |
|---|---|---|
| ITEM -1 — fix/471 | DONE | PR #472 hard-fails empty bootc deployments |
| ITEM 0b — strengthen dconf value assertions | DONE | PR #476 asserts shipped Bluefin dconf values |
| ITEM 1 — fix/bootc install silent failure | DONE | PR #472 landed the bootc install guard |
| ITEM 2 — `bluefin_extensions.feature` | DONE | PR #481 added per-UUID extension coverage |
| ITEM 3 — `bluefin_desktop.feature` | DONE | PR #484 added desktop identity checks |
| ITEM 4 — bctl suite | BACKLOG | Not covered in this sprint |
| ITEM 5 — named systemd service health checks | DONE | PR #479 added service health coverage |
| ITEM 6 — `flatpak_firstboot.feature` | DONE | PR #478 added first-boot Flatpak remote checks |
| ITEM 7 — `ujust` safe recipe smoke tests | DONE | PR #479 added `ujust` smoke checks |
| ITEM 8 — docs / skills update | DONE | Final cleanup recorded in this file, `suite-map.md`, `QA-REVIEW.md`, and related skills |
| ITEM A — AI/ML stack tests | BACKLOG | Still open after the sprint |
| ITEM B — shell sourcing integrity | DONE | PR #475 added shell sourcing coverage |
| ITEM C — Bazaar config YAML integrity | DONE | PR #475 added Bazaar YAML integrity coverage |
| ITEM D — polkit rules validation | DONE | PR #482 added polkit rules coverage |
| ITEM E — udev rules syntax check | DONE | PR #474 added udev syntax coverage |
| ITEM F — XDG portals and container runtime | DONE | PRs #474, #477, and #482 added portal and container runtime coverage |
| ITEM G — accessibility smoke tests | DONE | PR #473 added GNOME accessibility coverage |
| ITEM H — power management | BACKLOG | Still open after the sprint |

## Sprint delta by area

- **Smoke:** accessibility, MIME handler registration, per-UUID extension checks, desktop identity
- **Common:** dconf value assertions, shell sourcing, portal health, portal end-to-end checks, Flatpak remote state, service health, `ujust`, polkit, container runtime, zero layered RPM gate
- **Hardware:** udev syntax validation
- **E2E workflow / infra:** bootc install hard-fail guard, boot-time summary

## Remaining backlog

1. `bctl` / Bluefinctl coverage
2. AI/ML stack coverage (`ramalama`, `ollama`, `goose`, `llmfit`, AI Brewfiles)
3. Power management coverage (`power-profiles-daemon`, `upower`)

Keep those as separate follow-up slices rather than reopening this sprint bundle.

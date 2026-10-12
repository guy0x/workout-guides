# Navigation baseline — 2026-10-12

Recorded at the start of `feat/workout-navigation` (card t_749084c1).

## Pre-change counts (measured)

```
hub_guides= 177      # dirs in repo root containing index.html
icloud_guides= 149   # direct iCloud guide folders containing index.html
hub_html= 270679     # index.html bytes
program_html= 11322  # program.html bytes
```

## Publication state (measured 2026-10-12 ~18:15 IDT)

- `https://guides.guyovadia.com/` -> HTTP 200
- `/karin-avi-happier-spine-four-wall-mobility-drills_DeUvd7COzVv/` -> HTTP 200
- `/lebedanyaa-thoracic-expansion-asymmetrical-ribcage-drill_Dd9FNcSNEAx/` -> HTTP 200

Note: the plan audit earlier on 2026-10-12 saw these two newest child routes as 404.
They now resolve 200 — the deployment for the latest guides has landed. Publication
verification still treats contents-API 200 as insufficient on its own (report layers:
local files -> GitHub contents -> iCloud -> Pages route).

## Known drift

- Landing header displays 128 guides / 168 thumbnails while the hub has 177 guides
  (stale `sync_workout_guides.py` stat selectors; regression test planned in Phase 6).
- `program.html` displayed ISO week 39 while system date is ISO week 42 (hard-coded;
  must become current-ISO-week generated).
- iCloud mirror: 149 of 177 guide folders carry `index.html` -> 28 missing (additive
  repair candidates only; no deletions in this project).
- Notion backup reports 177/177 rows; Notion stays backup, not navigation truth.

## Constraints

- No guide deletion or renaming in this first pass.
- No bulk iCloud copy; apply mode is per-guide only, explicitly selected.
- Notion remains a backup, never navigation truth.
- Pre-existing untracked `scripts/__pycache__/` is build residue (ignored via .gitignore
  in the Phase 1 commit).

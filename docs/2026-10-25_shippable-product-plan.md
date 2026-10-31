# Workout Guides — Shippable Product Plan

**Date:** 2026-10-25
**Scope:** the static Workout Guides hub, `data/guides.json`, authored guide specs, iCloud `Workout Guides/`, `Wellness/Workouts/`, and reusable movement media.

## Inventory findings

- Current canonical navigation manifest: **174 guides / 856 exercise cards** (`data/guides.json`).
- Current navigation is static HTML with inline JavaScript; it supports guide search plus goal/gear filters, but not exercise-level discovery, body-part filtering, favorites, history, or structured progression.
- The minimum catalog schema has guide/card metadata only. It has no first-class exercise entity, aliases, muscles, movement pattern, laterality, difficulty, contraindications, evidence/provenance, or media variants.
- Metadata QA is not shippable yet: `metadata-gaps.json` reports **174 unknown / 0 complete**; mirror reconciliation reports **43 missing iCloud mirrors and 76 drifted**; the publication report verifies the Pages layer but does not make metadata completeness a release gate.
- The current source chain is split: authored specs → overrides → parsed HTML → generated catalog; iCloud is an additive mirror; Notion is backup. That contract is sound, but the exercise identity layer is missing.
- Several cards are polluted by transcription/OCR fragments or combined labels (for example, the `five-upper-body-exercises` cards and `Heavy DB / Incline Bench Press`). These must remain provenance-visible but should not be treated as clean canonical exercises.

## Product definition

A shippable product is a fast, offline-capable exercise and workout library where every guide and every exercise can be found, understood, previewed, and safely used from a phone. The product must preserve raw source wording while exposing a reviewed canonical layer.

### Release contract

1. Every published guide has a stable ID, source/provenance, status, thumbnail, and validated exercise cards.
2. Every exercise card resolves to a canonical exercise ID or an explicit `unresolved` record; no silent invented names.
3. Users can filter/search by goal, body part, muscle, equipment, location, duration, intensity, movement pattern, and exercise.
4. A user can open a guide, jump directly to an exercise, play its demo, and save/mark progress offline.
5. Broken links, missing media, duplicate IDs, invalid metadata, mirror drift, and unreviewed exercise labels fail CI before publication.
6. The public site remains static-hostable; no server is required for the first release.

## Target data model

Keep JSON as the canonical source layer, with generated denormalized JSON for the browser. Do not introduce SQLite until search scale or multi-user writes justify it.

```text
guides.json
  guide: id, title, author, source_url, source_reel_id, status,
         goals[], body_parts[], equipment[], locations[], duration_min,
         intensity, best_for[], avoid_if[], provenance, cards[]

exercises.json
  exercise: id, canonical_name, aliases[], category,
            primary_muscles[], secondary_muscles[], movement_pattern,
            equipment[], locations[], difficulty, laterality,
            instructions, cues[], regressions[], progressions[],
            safety_notes[], media[], review_status, provenance[]

relations.json
  guide_id + card_id -> exercise_id, position, dose, clip,
  target_role (primary/secondary/mobility), confidence, source_label

facets.json
  controlled vocabularies and display labels for muscles, equipment,
  goals, locations, movement patterns, difficulty, and target roles
```

Important rules:

- `source_label` is immutable evidence; `canonical_name` is reviewed data.
- Aliases are explicit: e.g. `Flat DB Press` and `Flat Dumbbell Press` can resolve to one exercise, while `Incline Dumbbell Bench Press` remains a distinct variant.
- Unknown/ambiguous cards are first-class and visible in admin QA; never discard them or silently merge them.
- A guide may contain both strength and mobility cards. `target_role` prevents a chest opener from being mixed into a chest hypertrophy result.

## Delivery phases

### Phase 0 — Freeze the contract and corpus (1–2 days)

- Declare `data/guides.json` as the navigation contract and add `data/exercises.json`, `data/relations.json`, and `data/facets.json`.
- Reconcile the 174 catalog guides against repo HTML, iCloud folders, and authored specs; produce a deterministic audit report.
- Preserve raw HTML/specs and add source hashes rather than rewriting source assets.
- Acceptance: every catalog ID has one authoritative source, one status, and a read-only reconciliation report.

### Phase 1 — Exercise extraction and review queue (3–5 days)

- Extract cards from specs/HTML into relation records.
- Add deterministic normalization for punctuation, case, equipment aliases, and common spelling variants.
- Seed canonical exercises from the current guides, circuits, Kettlebell catalogue, and health-tracker workout guides.
- Create a review queue for OCR fragments, combined labels, generic labels (`Chest push`), unnamed variations, and conflicting muscle tags.
- Acceptance: no card is unlinked; every link has `reviewed`, `needs_review`, or `unresolved` status and source evidence.

### Phase 2 — Catalog QA and release gates (2–3 days)

Add validators and tests for:

- schema and controlled vocabularies;
- unique stable IDs and card positions;
- broken guide/card/media URLs;
- missing thumbnails/GIFs;
- duplicate canonical exercises and alias collisions;
- stale generated timestamps;
- repo/iCloud mirror drift;
- unknown metadata and unresolved exercise labels;
- accessibility basics: headings, alt text, keyboard focus, reduced motion.

Make the release report fail on structural errors, but warn on explicitly approved unknowns. Do not claim a guide is product-ready while it remains in the unknown bucket.

### Phase 3 — Public interface v2 (4–7 days)

Keep the static-hosting model but generate a small app-like interface:

- **Home:** search, featured/latest, goal chips, compact stats.
- **Exercise directory:** canonical exercise cards with muscle, equipment, difficulty, aliases, demo, and “used in N guides.”
- **Guide directory:** filters for goals, body parts, equipment, location, duration, intensity, and reviewed status.
- **Guide detail:** clear summary, duration/equipment, ordered exercise list, per-card demo, dose, cues, regressions/progressions, source link, and deep-linkable `#exercise-id` anchors.
- **Chest/any-body-part result:** split direct strength, secondary work, and mobility so searches do not produce another misleading flat list.
- **Offline state:** localStorage for favorites, completed cards, last-opened guide, and filters; no account required.
- **Mobile UX:** sticky search/filter bar, large tap targets, lightweight poster frames, lazy media, and reduced-motion fallback.

### Phase 4 — Provenance, safety, and editorial tooling (3–5 days)

- Add source reel/guide links and capture date to every record.
- Add an internal review view for unresolved cards, duplicate candidates, missing metadata, and mirror drift.
- Add editorial actions that write specs/JSON only; generated HTML is never hand-edited.
- Keep medical language conservative: `avoid_if` is a plain-language movement caution, not diagnosis or treatment.

### Phase 5 — Performance and publication (2–3 days)

- Avoid base64 duplication in the browser bundle where possible; keep self-contained offline files as a deliberate export, but publish optimized poster/media assets for the web.
- Generate search indexes and faceted counts at build time.
- Add cache-busted assets, sitemap/robots metadata, canonical URLs, OpenGraph cards, and 404 handling.
- Run the existing build/check/verify scripts plus browser smoke tests against the published Pages routes.

### Phase 6 — Ship gate

Ship only when:

- catalog/schema tests pass;
- all published guide and exercise routes resolve;
- no high-severity unresolved metadata remains in the public result set;
- mirror/reconciliation report is reviewed;
- mobile keyboard/touch/accessibility smoke tests pass;
- offline favorite/progress behavior survives reload;
- the release report contains counts for guides, cards, canonical exercises, unresolved cards, missing media, and mirror drift.

## First implementation slice

The highest-value first slice is **exercise identity + chest search**:

1. Add `exercises.json` and `relations.json`.
2. Resolve the chest inventory and preserve ambiguous/unnamed entries in the review queue.
3. Build `/exercises/` and `/exercises/chest/` from the same generated data.
4. Add a guide card link to its canonical exercise page.
5. Add tests for aliases, duplicate collapse, unresolved labels, and chest facet counts.

This directly fixes the failure exposed by the chest query: the current system can search guide prose, but it cannot answer reliably because exercise identity and target roles are not modeled.

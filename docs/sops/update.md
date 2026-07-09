# SOP — Update existing refineries

**Goal:** research and stage edits to existing master records (fill blanks, refresh stale
values, add verified `[ref]`s). Recipe: `workflows.md` §3.

## Worklist

For the scope (country/region): rows with blank or stale key fields (status, capacity,
owner, config, coords), rows flagged in a prior build/reconciliation `conflicts`/`qa`
sheet, and rows missing `[ref]`s.

## Per row

1. Research each target field from **independent** sources (see `confidence_tiers.md`).
   Aim for ≥2 independent corroborations; a background dataset counts as one, medium.
2. Every URL passes `url_verifier.py` with the claimed value as the token — even URLs
   inherited from RMI/OGJ. gem.wiki / abarrelfull are rejected; chase the primary.
3. Stage `value + [ref]` together — no orphan `[ref]`, no unsourced value (estimates get
   `EstimatedCapacity?=Yes` + a Notes line instead of a fabricated URL).
4. New owner/parent → `entity_lookup.py` first (bare, then with `--country` only to
   annotate). Reuse existing entities.
5. Capacity always also fills `CapacityInKbpd` via `capacity_normalize`.

## Output

`batches/refineries_batch_<stamp>_<scope>_update.xlsx`, cell colors = confidence tier.
Never overwrite an existing batch file.

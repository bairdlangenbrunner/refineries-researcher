# SOP — Reconcile vs a background dataset

**Goal:** diff the main against a single background dataset to surface disagreements and
misses. Same engine as build's cross-source match, run one source at a time. Recipe:
`workflows.md` §5.

## Steps

1. `match.py --source <name> --against main --out batches/staging/match_<name>/` →
   matched pairs, source-only, main-only. The staging dir MUST be
   `batches/staging/match_<name>/` — `build_reconciliation_review.py` reads that path.
2. Classify:
   - **matched, agree** — no action (optionally mark re-verified/blue).
   - **matched, disagree** — per-field conflict → candidate for Update research. The
     background dataset is **one source, never authoritative**; verify, don't overwrite.
   - **source-only** — match to `OtherNames` first; genuine miss → Discovery.
   - **main-only** — refinery the dataset lacks; fine (our coverage is broader) unless it
     signals a retired/renamed record to check.
3. Findings are **candidates**, never auto-applied. A single Tier-2 dataset never reaches
   high alone.

## Escalate

Disagreement on >10% of matched rows (material capacity/owner/status), or >30 source-only
rows in one country. Both suggest a vintage/unit/coverage mismatch, not row-level findings.

## Output

`python scripts/build_reconciliation_review.py --source <name>` →
`batches/refineries_<name>_reconciliation_<stamp>.xlsx` (stamp = the main's stamp).
Sheets: `Summary` / `<name>_to_main` (matched pairs + per-field conflicts) /
`Main_dedup` (one source row hitting >1 main row) / `<name>_only` / `Possible`.
Fixes route to a follow-on Update batch.

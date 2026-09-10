# Workflow recipes

Command-by-command recipes. Read the relevant section + its SOP before starting a batch.
Stamp: `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`. Deliverables land under `batches/`.

---

## §1 Ingest a background source  (greenfield)  — SOP: `sops/ingest.md`

```bash
# 1. download the raw data into the manifest's file_path (gitignored). e.g. RMI from Drive.
# 2. normalize to canonical
python scripts/ingest.py --source rmi
# 3. eyeball the summary (row count, fill rates, capacity coverage)
cat sources/rmi/canonical_summary.json
```
Repeat per source. Registered: `rmi`, `ogj`, `ogim`, `china_rmi_tracker`, `eia`,
`india_ppac`, `brazil_anp`, `climate_trace`, `irs_rcn`, `gem_gci`. Confirm capacity units
resolved correctly — especially any tonnes/万吨/`'000 MT` source.

## §2 Build / refresh the main  (greenfield)  — SOP: `sops/build.md`

```bash
# merge the 8 mergeable sources (irs_rcn + gem_gci are overlay-only, `mergeable: false`
# in their manifests — merge.py hard-fails if they appear in --sources)
python scripts/merge.py \
    --sources rmi,ogj,ogim,china_rmi_tracker,eia,india_ppac,brazil_anp,climate_trace \
    --out data/main_<stamp>.parquet
python scripts/export_main.py            # -> batches/refineries_main_<stamp>_worldwide_export.xlsx
python scripts/export_possible_review.py   # -> batches/refineries_possible_review_<stamp>.xlsx
```
The build clusters the same physical refinery across sources (match.py), assigns stable
`RefineryID`s (via `data/id_crosswalk.json`, so ids survive rebuilds), fills crosswalk ids +
`SourcesPresent`, picks each field's value by per-field source priority, and routes
cross-source disagreements to `main_<stamp>.conflicts.parquet` (not silently resolved).
No `[ref]`s are filled here. `export_main.py` writes the reviewable worldwide xlsx;
`export_possible_review.py` writes the non-clustered `possible` pairs for threshold tuning.

## §3 Update existing refineries  (maintenance)  — SOP: `sops/update.md`

```bash
# worklist = stale/blank-ref rows in scope; research each, stage edits + verified [ref]s
python scripts/build_review_package.py --staging batches/staging/update_<run>/ \
    --output batches/refineries_batch_<stamp>_<scope>_update.xlsx   # ⛏ SKELETON — not yet implemented
```
Every staged value carries ≥1 verified `[ref]` (or `EstimatedCapacity?=Yes` + Notes). Run
`url_verifier.py` on every URL first (⛏ fetch/value-match is still manual — see
`scripts/README.md`).

## §4 Discover new refineries  — SOP: `sops/discovery.md`

```bash
python scripts/build_review_package.py --staging batches/staging/discovery_<run>/ \
    --output batches/refineries_batch_<stamp>_<scope>_discovery.xlsx   # ⛏ SKELETON — not yet implemented
```
Background-only rows → match to `OtherNames` before proposing as new. Escalate >5 new
clusters in one country.

## §5 Reconcile vs a background dataset  — SOP: `sops/reconciliation.md`

```bash
python scripts/match.py --source <name> --against main --out batches/staging/match_<name>/
python scripts/build_reconciliation_review.py --source <name>
#   -> batches/refineries_<name>_reconciliation_<stamp>.xlsx
#      sheets: Summary / <name>_to_main / Main_dedup / <name>_only / Possible
```
Same matcher as build, single source vs the main. The staging dir MUST be
`batches/staging/match_<name>/` — `build_reconciliation_review.py` reads that path. This
is the recipe every shipped reconciliation used (eia, india_ppac, brazil_anp,
climate_trace, and the overlay-only irs_rcn + gem_gci). Findings are candidates for
Update, never auto-applied.

## §6 Triage (plan the batch; memo)  — SOP: `sops/triage.md`

Output a markdown memo `batches/triage_<stamp>_ET.md`: coverage gaps, staleness, which
countries/sources to work next. No xlsx.

## §7 Quality control  — SOP: `sops/qc.md`

Data-health audit (missing coords, orphan `[ref]`s, out-of-vocab values, capacity
outliers, link rot). Memo `batches/qc_<stamp>_ET.md` (or an xlsx for large runs). QC
detects; Update fixes.

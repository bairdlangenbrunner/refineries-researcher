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
Repeat per source (`rmi`, `ogj`, `china_rmi_tracker`; `ogim` once its data layer is added).
Confirm capacity units resolved correctly — especially any tonnes/万吨 source.

## §2 Build / refresh the master  (greenfield)  — SOP: `sops/build.md`

```bash
python scripts/merge.py --sources rmi,ogj,china_rmi_tracker --out data/master_<stamp>.parquet
python scripts/build_review_package.py --staging batches/staging/build_<run>/ \
    --output batches/refineries_batch_<stamp>_build.xlsx
```
The build clusters the same physical refinery across sources (match.py), assigns stable
`RefineryID`s, fills crosswalk ids + `SourcesPresent`, and routes cross-source
disagreements to a `conflicts` sheet (not silently resolved). No `[ref]`s are filled here.

## §3 Update existing refineries  (maintenance)  — SOP: `sops/update.md`

```bash
# worklist = stale/blank-ref rows in scope; research each, stage edits + verified [ref]s
python scripts/build_review_package.py --staging batches/staging/update_<run>/ \
    --output batches/refineries_batch_<stamp>_<scope>_update.xlsx
```
Every staged value carries ≥1 verified `[ref]` (or `EstimatedCapacity?=Yes` + Notes). Run
`url_verifier.py` on every URL first.

## §4 Discover new refineries  — SOP: `sops/discovery.md`

```bash
python scripts/build_review_package.py --staging batches/staging/discovery_<run>/ \
    --output batches/refineries_batch_<stamp>_<scope>_discovery.xlsx
```
Background-only rows → match to `OtherNames` before proposing as new. Escalate >5 new
clusters in one country.

## §5 Reconcile vs a background dataset  — SOP: `sops/reconciliation.md`

```bash
python scripts/match.py --source ogj --against master --out batches/staging/recon_ogj_<run>/
python scripts/build_review_package.py --staging batches/staging/recon_ogj_<run>/ \
    --output batches/refineries_batch_<stamp>_<scope>_reconciliation.xlsx
```
Same matcher as build, single source vs the master. Findings are candidates for Update,
never auto-applied.

## §6 Triage (plan the batch; memo)  — SOP: `sops/triage.md`

Output a markdown memo `batches/triage_<stamp>_ET.md`: coverage gaps, staleness, which
countries/sources to work next. No xlsx.

## §7 Quality control  — SOP: `sops/qc.md`

Data-health audit (missing coords, orphan `[ref]`s, out-of-vocab values, capacity
outliers, link rot). Memo `batches/qc_<stamp>_ET.md` (or an xlsx for large runs). QC
detects; Update fixes.

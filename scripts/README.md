# scripts/

Engine + helpers. Import `paths` for the schema/paths and `capacity_normalize` for units;
don't re-derive either inline.

| Script | Status | Purpose |
|---|---|---|
| `paths.py` | ✅ done | Canonical paths + main schema column order (`SCHEMA`, `ordered_columns`, `latest_main`) + controlled vocab lists. |
| `capacity_normalize.py` | ✅ done | Capacity → kbpd. Handles the `Mt/a`, 万吨/`tttpa`, and `'000 MT`/yr (`kt/a`) traps. Run it directly for the self-check. |
| `country_normalize.py` | ✅ done | Country/ISO3 normalization used to block matches by country. |
| `ingest.py` | ✅ works | Background source → canonical parquet via `sources/<name>/manifest.yml` (+ adapter). Greenfield step 1. |
| `match.py` | ✅ works | Hybrid matcher: cKDTree coord-blocking pass + a country-blocked greedy-1:1 pass (name + capacity) for coordless sources. Used by build & reconciliation; writes `matches.parquet` + `match_summary.json`. |
| `merge.py` | ✅ works | Cluster matched sources (union-find, same-source guard) → one main record per refinery on the GEM schema. Writes `main_*.parquet` + `.build.json`/`.conflicts`/`.possible`. Greenfield step 2. |
| `export_main.py` | ✅ works | Latest main → `batches/refineries_main_<stamp>_worldwide_export.xlsx` (drops `RefineryID`). |
| `export_possible_review.py` | ✅ works | Latest main's `possible` pairs → `batches/refineries_possible_review_<stamp>.xlsx` for threshold tuning. |
| `build_reconciliation_review.py` | ✅ works | A `batches/staging/match_<src>/` run → `batches/refineries_<src>_reconciliation_<stamp>.xlsx` (matched / possible / background-only). Used for reconciliation + the irs_rcn overlay. |
| `build_china_undermerge_review.py` | ✅ works | Resolves the China under-merge: hunts merge candidates for the **solo** china_rmi_tracker teapots (those still china-only in the main, read from the main's 1:1 `china_id` column — NOT the anchor-keyed `id_crosswalk.json`) vs the NON-tracker China main rows → `batches/refineries_china_undermerge_<stamp>.xlsx`. Already-merged teapots go to an `Already_merged` sheet (no action). Bridges teapot company-names to RMI plant-names via the tracker's own `RMIFacilityName` column (present only in the live "…- main" export, `data/china_gem_main_tracker.xlsx`). Proximity-only pairs are demoted (dense-park false-match guard). |
| `entity_lookup.py` | ⛏ skeleton | De-dup owners/parents against shared GEM entities before staging. Blocked on a shared-entity source (no live GRT backend yet). |
| `url_verifier.py` | ⛏ partial | Confirm a URL contains the claimed value. Host-block (gem.wiki/globalenergymonitor/abarrelfull) is **live**; fetch + value-match still TODO. |
| `build_review_package.py` | ⛏ skeleton | Staged JSON → reviewable batch xlsx (colors = confidence, `[ref]` GUARD). |

## Typical invocation order (greenfield)

```bash
# 1. ingest each source to canonical
python scripts/ingest.py --source rmi
python scripts/ingest.py --source ogj
python scripts/ingest.py --source ogim
python scripts/ingest.py --source china_rmi_tracker

# 2. build the main by clustering across the mergeable sources (irs_rcn is overlay-only)
python scripts/merge.py \
    --sources rmi,ogj,ogim,china_rmi_tracker,eia,india_ppac,brazil_anp,climate_trace \
    --out data/main_<stamp>.parquet
python scripts/export_main.py                 # -> batches/refineries_main_<stamp>_worldwide_export.xlsx
python scripts/export_possible_review.py        # -> batches/refineries_possible_review_<stamp>.xlsx

# 3. reconcile an overlay-only source against the main -> review workbook (irs_rcn)
python scripts/match.py --against main --source irs_rcn --out batches/staging/match_irs_rcn/
python scripts/build_reconciliation_review.py --source irs_rcn
```

## Building out the skeletons

The three ⛏ scripts (`entity_lookup`, `url_verifier` fetch/match, `build_review_package`)
have working siblings in `../lng-terminals-researcher/scripts/` and
`../pipelines-researcher/scripts/` — same patterns (staging JSON, confidence colors,
`[ref]` GUARD, entity dedup). Refineries are **point features**, so `match.py` geometry is
a plain haversine, not route overlap. Port + adapt rather than writing from scratch.

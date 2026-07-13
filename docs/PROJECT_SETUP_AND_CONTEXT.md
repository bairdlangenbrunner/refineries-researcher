# Project setup & context

## What this is

Backend scaffolding for building and maintaining GEM's worldwide refinery
database (working name **GRT — Global Refinery Tracker**). Sibling of the
`lng-terminals-researcher`, `lng-carriers-researcher`, and `pipelines-researcher` repos and
built to the same conventions, but **greenfield**: there is no live GEM refineries backend
yet, so the first job is assembling the initial database from background datasets.

Researcher: Baird Langenbrunner (initials **BL**). The agent never publishes and never
machine-overwrites the curated main — it produces reviewable xlsx + staged JSON that
Baird applies by hand.

## The greenfield pipeline

```
   mergeable sources ─ingest.py──▶ canonical parquets ──merge.py──▶ main ──▶ Update/Discover/QC
   (rmi, ogj, ogim, china,         (one schema)         (GEM schema,
    eia, india_ppac,                                     RefineryIDs)      ▲
    brazil_anp, climate_trace)                                            │ reconcile (match.py +
   overlay-only ─────ingest.py──▶ canonical parquet ───────────────────┘  build_reconciliation_review.py)
   (irs_rcn)                                             -> review workbook (never merged)
```

1. **Ingest** each source to the canonical schema (`ingest.py`, per source).
2. **Build** the main by clustering across the 8 mergeable sources (`merge.py`/`match.py`).
3. **Reconcile** the overlay-only source (`irs_rcn`) against the main → a review workbook
   (`match.py` + `build_reconciliation_review.py`). Same engine reconciles any single source.
4. **Update / Discover / QC** — ongoing maintenance, same as the siblings.

## Background sources (9 registered — see `docs/reference/source_roster.md`)

**Mergeable — clustered into the main** (`merge.py --sources`):
- **RMI Refinery List (Feb '23)** — 484 rows, primary seed. Drive folder
  `1gJaJ7KYByNAHzoF0ve6ienuEvsfP28bV`, file `15CoiFuiT-JtDD-cb3ZV-Cx_Qb8RUPiDk`.
- **OGJ Worldwide Refining survey** — 577 rows, rebuilt from the WW Refining PDF (country
  on every row; no coordinates). Europe-only map-JSON adapter kept as `adapter_mapjson.py`.
- **OGIM v2.7** — 692 rows, refineries GIS layer (coordinate corroboration); gpkg at
  `/Users/baird/Dropbox/_gis-data/ogim/OGIM_v2.7.gpkg`.
- **GEM China Independent Oil Refinery Tracker for RMI** — 101 rows, schema template + China
  seed; Google Sheet `1PyNUtGUDLdY1chJ-MkzzgV_OnAcNTp2QlIq8jLhStPw`. GEM-authored → seed
  only, never citable.
- **EIA Refinery Capacity Report (Form EIA-820)** — 124, US crude, Tier 1 gold standard;
  coord-bearing. Priority source for US capacity/status/owner. Citable (federal public domain).
- **India PPAC installed capacity** (1 Apr 2025) — 23, India, Tier 1; ⚠ `'000 MT`/yr unit;
  coordless → country-blocked match. Priority for India capacity. Citable `.gov.in`.
- **Brazil ANP Anuário Tbl 2.29** (31/12/2024) — 18, Brazil, Tier 1; bbl/day; coordless.
  Priority for Brazil capacity + start year. Citable federal open data.
- **Climate TRACE refining assets** (v5.8.0) — 728 worldwide, Tier 2, independent →
  citable (CC BY 4.0); coord+capacity+config. Nameplate capacity runs high → ranked **last**
  for capacity (fills genuine-miss rows only; overlaps go to the conflicts report).

**Overlay-only — never merged:**
- **IRS Active Fuel Refineries (RCN) registry** — 227, US, Tier 1; tax definition, no
  capacity/coords → capacity-gated matcher never auto-matches. **OVERLAY ONLY** (Baird's
  ruling); reconciled into `batches/refineries_irs_rcn_reconciliation_*.xlsx`.

## Open decisions (greenfield surface — get Baird's ruling, then log it)

- **Scope boundaries:** condensate splitters, topping/mini refineries, associated-vs-
  standalone petrochemical, bio/GTL/CTL exclusion edge cases → `controlled_vocab.md`
  "Scope-boundary rulings".
- **Match thresholds** for `merge.py` clustering (name/distance/capacity weights) →
  `sops/build.md`.
- **Entity source** for `entity_lookup.py` until a live backend exists (union of main +
  `../gem-database-access/` exports?).
- **Tracker name/abbrev** (GRT is a working name) and eventual publication surface.
- **Capacity basis:** nameplate/design (RMI) vs distillation vs throughput — decide the
  main's canonical basis and note conversions.

## Status of the build (update as it evolves)

- ✅ Repo scaffold, schema, controlled vocab, capacity conversions, source registry, ingest
  engine, all 9 source manifests + adapters.
- ✅ **Ingest**: all 9 sources → `sources/<name>/canonical.parquet`. Seed: rmi 484, ogj 577
  (WW Refining PDF, country on every row, no coords), ogim 692, china_rmi_tracker 101. Later:
  eia 124, india_ppac 23, brazil_anp 18, climate_trace 728, irs_rcn 227. Sentinel handling:
  capacity `<=0` (RMI `0`, OGIM `-999`) and OGIM's `1900` start-year placeholder null out;
  `tttpa`, `Mt/a`, and `'000 MT`/yr → kbpd all verified in `capacity_normalize`.
- ✅ **Build**: `match.py` (cKDTree coord-blocking pass + COUNTRY-blocked greedy-1:1 pass for
  coordless sources) and `merge.py` (union-find, same-source guard) built; `country_normalize.py`
  added. Latest union main `data/main_20260713_1416_ET.parquet`: **2747 → 1260 rows**,
  706 multi-source clusters, 291 conflicts, 1258 `possible` pairs, IDs `R####` with
  `data/id_crosswalk.json`. **Built from all 8 mergeable sources** (rmi, ogj, ogim,
  china_rmi_tracker, eia, india_ppac, brazil_anp, climate_trace). Every row `InScope=unknown`
  (superset-first; scope is Phase B). climate_trace's worldwide coords collapsed many former
  single-source rows into multi-source clusters (706, up from 456 in the 4-source build).
- ✅ **Coordless matching** (Baird chose greedy 1:1 + capacity): `match.py`'s country-blocked
  pass handles pairs the coord pass can't reach (≥1 side coordless). Within a country
  `token_set_ratio` pins to ~1.0 for every same-city row, so **name can't separate refineries
  in one city — capacity is the discriminator.** Scores `0.6*name + 0.4*capacity`, greedy 1:1
  assignment, capacity gate (name≥0.85 & cap≥0.90, or name≥0.72 & cap≥0.95). `china_rmi_tracker`
  had no Country column → generic `defaults: {country: China, iso3: CHN}` block in `ingest.py`.
- ✅ **All mergeable sources merged** (this build): `merge.py` extended so `eia`, `india_ppac`,
  `brazil_anp`, `climate_trace` participate — new crosswalk id columns in `paths.py`
  (`eia_id`/`climate_trace_id`/`india_ppac_id`/`brazil_anp_id`), per-field priority + anchor
  order in `merge.py` (see `sops/build.md`). EIA (US), india_ppac, brazil_anp rank first for
  their country's capacity/status; climate_trace nameplate ranks last for capacity. Genuine
  misses now carried IN the main: climate_trace → Dangote (NGA 650), Pemex Olmeca/Dos Bocas
  (MEX 340), Duqm (OMN 230); brazil_anp → Ssoil Energy (Coroados SP, 12.5 kbpd).
- ✅ **Exports + reconciliation**: `export_main.py` (worldwide export xlsx, drops RefineryID),
  `export_possible_review.py` (possible-pairs review), and `build_reconciliation_review.py`
  (`match_<src>/` → per-source review workbook; fixed to tolerate a 0-match source). `irs_rcn`
  is reconciled against the main (overlay-only) → `batches/refineries_irs_rcn_reconciliation_*.xlsx`.
- ⛏ **Still skeletons**: `build_review_package.py` (staged JSON → batch xlsx), `entity_lookup.py`
  (blocked on a shared-entity source), `url_verifier.py` fetch/value-match (host-block is live).
- ✅ **China under-merge** (review workbook shipped): `build_china_undermerge_review.py` reconciles
  the 101 china-tracker rows vs the non-tracker China main rows and emits
  `batches/refineries_china_undermerge_<stamp>.xlsx` — per-teapot merge candidates for Baird to
  collapse by hand. Key: the tracker's own `RMIFacilityName` column (the teapot→RMI plant-name
  bridge) lives ONLY in the live "…- main" export, not the registered "…for RMI" one, so the
  script reads `data/china_gem_main_tracker.xlsx` for it. Which teapots are still solo is read
  from the main's own **`china_id` column** (a clean 1:1 record of the china_rmi_tracker
  source_id in each cluster), NOT `id_crosswalk.json`. Against main `1416`: **61 teapots are
  already merged** (Climate TRACE coords folded them in — resolved, listed in an Already_merged
  sheet, no action) and **40 are solo** (the genuine under-merge surface); of the 40 solo, 25 get
  a candidate (14 high-confidence via the RMIname bridge) and 15 have none. Proximity-only pairs
  are demoted to `low` + an `ambiguous` flag — dense Shandong/Dongying parks over-match on
  coordinates (the exact trap flagged earlier). Still MANUAL to apply (agent never merges).
- ℹ **`id_crosswalk.json` is anchor-keyed by design** (not a bug): `merge.py:_assign_ids` writes
  ONE key per cluster — `<anchor_source>:<id> → R####` for the cluster's single highest-priority
  source (anchor order rmi > ogj > ogim > china_rmi_tracker > eia > climate_trace > india_ppac >
  brazil_anp). So a teapot that merged under an RMI/OGJ anchor (e.g. Hengli Dalian, Sinochem
  Quanzhou, Shenghong Lianyungang) legitimately has no `china_rmi_tracker:` key — it's already
  merged, not missing. To map every per-source id to its main row, use the main's per-source
  id columns (`china_id`, `rmi_refine_id`, `ogj_id`, …), which are complete and 1:1.
- ☐ Review the `possible` pairs (`data/main_*.possible.parquet`, now 1258) to tune thresholds
  — the count grew with the added sources; watch for climate_trace/eia US near-duplicates.
- ☐ **Phase B scope pass**: set `InScope`/`ScopeReason` per the open scope-boundary decisions above.
- ☐ First reviewable batch xlsx (needs `build_review_package.py`).

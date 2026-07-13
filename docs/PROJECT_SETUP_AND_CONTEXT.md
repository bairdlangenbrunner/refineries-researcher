# Project setup & context

## What this is

Backend scaffolding for building and maintaining GEM's worldwide crude-oil refinery
database (working name **GORT — Global Oil Refinery Tracker**). Sibling of the
`lng-terminals-researcher`, `lng-carriers-researcher`, and `pipelines-researcher` repos and
built to the same conventions, but **greenfield**: there is no live GEM refineries backend
yet, so the first job is assembling the initial database from background datasets.

Researcher: Baird Langenbrunner (initials **BL**). The agent never publishes and never
machine-overwrites the curated master — it produces reviewable xlsx + staged JSON that
Baird applies by hand.

## The greenfield pipeline

```
   background sources ──ingest.py──▶ canonical parquets ──merge.py──▶ master ──▶ Update/Discover/QC
   (rmi, ogj, ogim,                  (one schema)         (GEM schema,
    china_rmi_tracker)                                     RefineryIDs)
```

1. **Ingest** each source to the canonical schema (done for the format; run per source).
2. **Build** the master by clustering across sources (`merge.py`/`match.py` — skeletons).
3. **Update / Discover / Reconcile / QC** — ongoing maintenance, same as the siblings.

## Background sources (see `docs/reference/source_roster.md`)

- **RMI Refinery List (Feb '23)** — ~800 rows, primary seed. Drive folder
  `1gJaJ7KYByNAHzoF0ve6ienuEvsfP28bV`, file `15CoiFuiT-JtDD-cb3ZV-Cx_Qb8RUPiDk`.
- **OGJ Worldwide Refining survey** — map JSON + PDF in `../refineries-tracker/`.
- **OGIM v2.7** — refineries GIS layer; docs at `/Users/baird/Dropbox/_gis-data/ogim/`,
  data layer still to be added.
- **GEM China Independent Oil Refinery Tracker for RMI** — the schema template + China
  seed; Google Sheet `1PyNUtGUDLdY1chJ-MkzzgV_OnAcNTp2QlIq8jLhStPw`. GEM-authored → seed
  only, never citable.

## Open decisions (greenfield surface — get Baird's ruling, then log it)

- **Scope boundaries:** condensate splitters, topping/mini refineries, associated-vs-
  standalone petrochemical, bio/GTL/CTL exclusion edge cases → `controlled_vocab.md`
  "Scope-boundary rulings".
- **Match thresholds** for `merge.py` clustering (name/distance/capacity weights) →
  `sops/build.md`.
- **Entity source** for `entity_lookup.py` until a live backend exists (union of master +
  `../gem-database-access/` exports?).
- **Tracker name/abbrev** (GORT is a working name) and eventual publication surface.
- **Capacity basis:** nameplate/design (RMI) vs distillation vs throughput — decide the
  master's canonical basis and note conversions.

## Status of the build (update as it evolves)

- ✅ Repo scaffold, schema, controlled vocab, capacity conversions, source registry + 4
  manifests, ingest engine, OGJ adapter.
- ✅ **A1–A2 ingest**: all 4 sources → `sources/<name>/canonical.parquet` (rmi 484, ogim 692,
  ogj 127 Europe-only, china_rmi_tracker 101). Sentinel handling: capacity `<=0` (RMI `0`,
  OGIM `-999`) and OGIM's `1900` start-year placeholder null out; `tttpa`→kbpd verified.
- ✅ **A3 build**: `match.py` (cKDTree coord-blocking + name/haversine/capacity scoring) and
  `merge.py` (union-find with same-source guard) built; `country_normalize.py` added.
  First union master: **1404 → 1060 rows**, 293 multi-source, 193 conflicts, IDs `R####` with
  `data/id_crosswalk.json`. Every row `InScope=unknown` (superset-first; scope is Phase B).
- ⛏ `entity_lookup.py` / `url_verifier.py` / `build_review_package.py` — still skeletons.
- ☐ **A4 dedup follow-ups**:
  (1) China under-merge — diagnosed: the `Is_In_RMI_20230508` flag marks 43 china-tracker
  rows as RMI duplicates but only 9 merge (china uses *company* names, RMI uses *plant*
  names → pairs land in `possible`). Coordinates can't safely finish it: only 15/43 have any
  RMI neighbor ≤15 km and the nearest-neighbor pairs include clear false matches (dense
  Shandong/Dongying teapot parks). Needs a review worksheet or a name/capacity assignment,
  not proximity auto-merge. STILL OPEN.
  (2)+(3) ✅ **OGJ rebuilt from the WW Refining PDF** (`sources/ogj/adapter.py`, replaces the
  Europe-only map JSON now in `adapter_mapjson.py`): 577 refineries, 105 countries, country on
  EVERY row (fixes the 55 country-less), Crude b/cd → kbpd. Reconciles with PDF section
  Totals except 3 documented PDF quirks. Trade-off: **no coordinates**.
  ✅ **Coordless-blocking solved** (Baird chose greedy 1:1 + capacity). `match.py` now has a
  second, COUNTRY-blocked pass for pairs the coord pass can't reach (≥1 side coordless).
  Within a country, `token_set_ratio` pins to ~1.0 for every same-city row (a short source
  name is a token-subset of OGJ's long `owner—operator—city` string), so **name can't
  separate refineries in one city — capacity is the discriminator.** The pass scores each
  pair on a `0.6*name + 0.4*capacity` composite and runs a **greedy 1:1 assignment** (each
  row on both sides matched at most once); `match` requires a capacity gate (`_country_labels`:
  name≥0.85 & cap≥0.90, or name≥0.72 & cap≥0.95). Unmatched OGJ rows keep surviving candidates
  as `possible` (review queue). Fan-out is structurally 0. `china_rmi_tracker` had no Country
  column → added `defaults: {country: China, iso3: CHN}` (new generic `defaults:` block in
  `ingest.py`). OGJ dedup counts (match/possible): rmi 162/136, ogim 220/299, china 4/13.
  (4) Review the `possible` pairs (`data/master_*.possible.parquet`) to tune thresholds.
- ☐ **Phase B scope pass**: set `InScope`/`ScopeReason` per the open scope-boundary decisions above.
- ☐ First reviewable batch xlsx (needs `build_review_package.py`).

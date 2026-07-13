# refineries-researcher

Backend scaffolding for building and maintaining **Global Energy Monitor's worldwide
refinery database** (working name **GRT — Global Refinery Tracker**). Sibling
of `lng-terminals-researcher`, `lng-carriers-researcher`, and `pipelines-researcher`; same
conventions, but **greenfield** — the first job is assembling the initial database from
several background datasets, then maintaining it.

The agent never publishes and never machine-overwrites the curated main. Every batch
produces a reviewable Excel deliverable + staged JSON that the researcher applies by hand.

## Layout

```
CLAUDE.md                     operational guide (read this first)
docs/
  workflows.md                command recipes per workflow
  sops/                       ingest, build, update, discovery, reconciliation, triage, qc
  reference/                  gem_schema, controlled_vocab, capacity_units,
                              confidence_tiers, source_roster, workbook_conventions
  country_notes/              per-country findings
  PROJECT_SETUP_AND_CONTEXT.md
sources/                      pluggable background-dataset registry (9 sources) —
                              manifest.yml (+ adapter.py) each; see sources/README.md
scripts/                      ingest / match / merge / export_main / export_possible_review /
                              build_reconciliation_review / build_review_package /
                              entity_lookup / url_verifier (+ paths, capacity_normalize,
                              country_normalize)
data/                         main_*.parquet (+ .build.json/.conflicts/.possible) + gitignored raw
batches/                      xlsx deliverables + staging/ (match_<src>/ per reconciliation run)
tests/
```

## Quick start

```bash
pip install -r requirements.txt
python scripts/capacity_normalize.py                        # self-check the unit conversions
python scripts/ingest.py --source rmi                       # background source -> canonical.parquet
python scripts/merge.py \
    --sources rmi,ogj,ogim,china_rmi_tracker,eia,india_ppac,brazil_anp,climate_trace \
    --out data/main_<stamp>.parquet                       # irs_rcn is overlay-only, never merged
python scripts/export_main.py                             # latest main -> worldwide export xlsx
```

## Background sources (9 registered)

Full detail — row counts, unit traps, quirks, citability — in `docs/reference/source_roster.md`.

| Source | Scope | Role | Citable? |
|---|---|---|---|
| `rmi` — RMI Refinery List (Feb '23) | worldwide (484) | primary global seed; capacity + ISO3 + config, no status | no |
| `ogj` — OGJ Worldwide Refining survey | worldwide (577) | capacity/owner/status; country on every row; **no coords** | no |
| `ogim` — OGIM v2.7 refineries layer | worldwide (692) | location/coordinate corroboration (GIS) | yes |
| `china_rmi_tracker` — GEM China tracker | China (101) | schema template + China seed; GEM-authored | **no** |
| `eia` — EIA Refinery Capacity Report (Form EIA-820) | US (124) | US capacity gold standard; b/cd + coords; **merged** | yes |
| `india_ppac` — India PPAC installed capacity | India (23) | national capacity anchor; ⚠ `'000 MT`/yr unit; coordless; **merged** | yes |
| `brazil_anp` — Brazil ANP Anuário Tbl 2.29 | Brazil (18) | national capacity + start-year anchor; bbl/day; coordless; **merged** | yes |
| `climate_trace` — Climate TRACE refining assets (v5.8.0) | worldwide (728) | independent coord+capacity+config; **merged**; nameplate runs high | yes |
| `irs_rcn` — IRS Active Fuel Refineries registry | US (227) | **OVERLAY ONLY, never merged**; tax def, no capacity/coords | yes |

Note: every `citable` source's URLs still pass `url_verifier.py` before they can be a
`[ref]`; GEM/gem.wiki and `abarrelfull.wikidot.com` are never citable, even when a source
dataset cites them.

## Status (greenfield)

**Union main built** from the eight mergeable sources (`rmi, ogj, ogim, china_rmi_tracker,
eia, india_ppac, brazil_anp, climate_trace`): latest `data/main_20260713_1416_ET.parquet` —
**1260 rows** from 2747 input, 706 multi-source clusters, 291 conflicts, 1258 `possible`
pairs queued for review. Every row is `InScope=unknown` (superset-first; the Phase-B scope
pass is pending). Per-field source priority (in `merge.py`) puts the Tier-1 gov sources
first for their own country (EIA for US capacity/status/owner; india_ppac/brazil_anp for
national capacity), RMI as the global design-capacity backbone, and climate_trace's
nameplate capacity **last** (it runs high vs operating figures → only fills genuine-miss
rows; overlaps go to the conflicts report, never adopted).

`irs_rcn` is **overlay-only by ruling** — never merged; it is reconciled against the main
into `batches/refineries_irs_rcn_reconciliation_*.xlsx` for hand-worked US discovery.

**Engine done:** `ingest`, `match` (cKDTree coord-blocking + country-blocked greedy-1:1),
`merge`, `export_main`, `export_possible_review`, `build_reconciliation_review`,
`capacity_normalize`, `country_normalize`, `paths`.
**Still skeletons:** `build_review_package` (staged JSON → batch xlsx), `entity_lookup`
(needs a shared-entity source), `url_verifier` fetch/match (host-block logic is live).

See `docs/PROJECT_SETUP_AND_CONTEXT.md` for the full build log and open decisions.

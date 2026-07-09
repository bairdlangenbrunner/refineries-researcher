# Source roster

Background datasets registered under `sources/`, plus preferred independent research
sources. **None of the GEM-authored datasets is citable** — they are seed/reconciliation
data. `source_tier` drives confidence (see `confidence_tiers.md`).

## Registered background datasets (`sources/<name>/manifest.yml`)

Row counts below are ingested canonical rows (see each `sources/<name>/canonical_summary.json`).

| name | What it is | Rows | Key fields | Tier | Notes |
|---|---|---|---|---|---|
| `rmi` | RMI Refinery List (February '23) | 484 worldwide | id, name, design capacity (bbl/day), country, ISO3, lat/lon, WKT, type (H/M/D), typology source | 2 | Primary global seed; near-full capacity + ISO3 + configuration, **no status column**, cap `0`/`<=0` = unknown/idle. Drive: `Copy of RMI Refinery List (February '23).xlsx` in folder `1gJaJ7KYByNAHzoF0ve6ienuEvsfP28bV` (fileId `15CoiFuiT-JtDD-cb3ZV-Cx_Qb8RUPiDk`). Many `Typology Source` cells are `abarrelfull.wikidot.com` — **not citable**, chase the primary. |
| `ogj` | Oil & Gas Journal — map JSON export | 127 (**Europe only**) | owner, capacity (kbbl/cd + Mt/a), status, name, lat/lon; 2009–2023 time series | 2 | The registered `refineries.json` (`../refineries-tracker/`) is a **Europe-only** interactive-map export, NOT the worldwide survey; adapter takes the latest year (2023) and carries `Mt/a` for the ×20.08 cross-check. **Worldwide OGJ (~700) lives in the WW Refining PDF** + extraction notebook in `../refineries-tracker/` — a separate source to register when needed. |
| `ogim` | OGIM v2.7 `Crude_Oil_Refineries` layer | 692 worldwide | GIS points; design + throughput bpd, location-focused | 2 | **Location source**: coords 100%, capacity 600/692 (`-999` sentinel nulled) — but status 79% `N/A` and start-year 98% `1900` sentinel, so weak on status/vintage. `SRC_REF_ID` is an ID into OGIM's own catalog, not a URL. gpkg at `/Users/baird/Dropbox/_gis-data/ogim/OGIM_v2.7.gpkg` (3 GB, read single layer). |
| `china_rmi_tracker` | GEM China Independent Oil Refinery Tracker for RMI | 101 (China) | full GEM `[ref]`-paired schema + data dictionary | — | **Schema template** for the whole project + China seed data; fully populated, `tttpa`→kbpd verified to 0.1% vs the sheet's own column. GEM-authored → **seed only, never a citation.** Sibling tab "Extra facilities (out of scope)" (43 rows) is a Phase-B scope signal. Drive: Google Sheet `1PyNUtGUDLdY1chJ-MkzzgV_OnAcNTp2QlIq8jLhStPw`. |

## Preferred independent research sources (for `[ref]` corroboration)

- Company/operator sites, annual reports, investor decks (primary).
- National regulators / energy ministries / statistics agencies (primary).
- EIA, JODI, OPEC, IEA reports (secondary, authoritative).
- Reputable trade press: Reuters, Argus, S&P Global (Platts), Hydrocarbon Processing,
  Oil & Gas Journal articles, Upstream, hydrocarbons-technology.com.
- **Not independent / not citable:** gem.wiki, globalenergymonitor.org, anything tracing
  to GEM, `abarrelfull.wikidot.com` (community wiki that echoes GEM/OGJ — chase its
  footnote), Wikipedia when it merely footnotes one of the above (cite the footnote).

# Source roster

Background datasets registered under `sources/`, plus preferred independent research
sources. **None of the GEM-authored datasets is citable** — they are seed/reconciliation
data. `source_tier` drives confidence (see `confidence_tiers.md`).

## Registered background datasets (`sources/<name>/manifest.yml`)

| name | What it is | Rows | Key fields | Tier | Notes |
|---|---|---|---|---|---|
| `rmi` | RMI Refinery List (February '23) | ~800 worldwide | id, name, design capacity (bbl/day), country, ISO3, lat/lon, WKT, type (H/M/D), typology source | 2 | Primary global seed. Drive: `Copy of RMI Refinery List (February '23).xlsx` in folder `1gJaJ7KYByNAHzoF0ve6ienuEvsfP28bV` (fileId `15CoiFuiT-JtDD-cb3ZV-Cx_Qb8RUPiDk`). Many `Typology Source` cells are `abarrelfull.wikidot.com` — **not citable**, chase the primary. |
| `ogj` | Oil & Gas Journal Worldwide Refining survey | ~700 | owner, capacity (kbbl/cd + Mt/a), status, name, lat/lon | 2 | Industry standard. Two artifacts: the year-keyed map JSON (`../refineries-tracker/refineries.json`) and the WW Refining PDF + extraction notebook in `../refineries-tracker/`. Carries dual capacity units — good for the Mt/a↔kbpd cross-check. |
| `ogim` | OGIM v2.7 refineries layer | — | GIS point features, location-focused | 2 | Oil & Gas Infrastructure Mapping. Docs at `/Users/baird/Dropbox/_gis-data/ogim/` (README + data-source-references PDFs); the geopackage/data layer to be added. Best used for coordinate corroboration. |
| `china_rmi_tracker` | GEM China Independent Oil Refinery Tracker for RMI | ~? (China) | full GEM `[ref]`-paired schema + data dictionary | — | **Schema template** for the whole project + China seed data. GEM-authored → **seed only, never a citation.** Drive: Google Sheet `1PyNUtGUDLdY1chJ-MkzzgV_OnAcNTp2QlIq8jLhStPw`. |

## Preferred independent research sources (for `[ref]` corroboration)

- Company/operator sites, annual reports, investor decks (primary).
- National regulators / energy ministries / statistics agencies (primary).
- EIA, JODI, OPEC, IEA reports (secondary, authoritative).
- Reputable trade press: Reuters, Argus, S&P Global (Platts), Hydrocarbon Processing,
  Oil & Gas Journal articles, Upstream, hydrocarbons-technology.com.
- **Not independent / not citable:** gem.wiki, globalenergymonitor.org, anything tracing
  to GEM, `abarrelfull.wikidot.com` (community wiki that echoes GEM/OGJ — chase its
  footnote), Wikipedia when it merely footnotes one of the above (cite the footnote).

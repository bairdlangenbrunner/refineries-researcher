# Background-source registry

Each background refinery dataset is registered here as `sources/<name>/manifest.yml`
(declarative column map + units + status/config maps + tier) plus an optional
`adapter.py` for nonstandard formats. `scripts/ingest.py` reads the manifest, normalizes
the source into the **canonical record** (`_schema/canonical_record.md`), and writes
`sources/<name>/canonical.parquet` (gitignored) + `canonical_summary.json` (committed).

**Adding a dataset is config, not engine code:** drop a manifest, run
`python scripts/ingest.py --source <name>`.

## Registered

Row counts are ingested canonical rows (see each `canonical_summary.json`). Full detail —
unit traps, quirks, merge status — in `docs/reference/source_roster.md`.

| dir | source | scope / rows | tier | citable | notes |
|---|---|---|---|---|---|
| `rmi/` | RMI Refinery List (Feb '23) | worldwide, 484 | 2 | no | primary global seed; capacity + ISO3 + config, no status column |
| `ogj/` | OGJ Worldwide Refining survey | worldwide, 577 | 2 | yes | owner/city/status; country on every row; rebuilt from WW Refining PDF; **no coords** |
| `ogim/` | OGIM v2.7 refineries layer | worldwide, 692 | 2 | no | GIS; coordinate/location corroboration |
| `china_rmi_tracker/` | GEM China Independent Oil Refinery Tracker | China, 101 | — | **no** | schema template + China seed; GEM-authored, seed only |
| `eia/` | EIA Refinery Capacity Report (Form EIA-820) | US, 124 | 1 | yes | US capacity gold standard; b/cd + coords; adapter pivots long workbook; **mergeable** |
| `india_ppac/` | India PPAC installed refining capacity | India, 23 | 1 | yes | national anchor; ⚠ `'000 MT`/yr unit; coordless |
| `brazil_anp/` | Brazil ANP Anuário 2025, Table 2.29 | Brazil, 18 | 1 | yes | national anchor; bbl/day; no operator/coords/status |
| `climate_trace/` | Climate TRACE `oil-and-gas-refining` (v5.8.0) | worldwide, 728 | 2 | yes | independent coord+capacity+config; **mergeable**; nameplate runs high |
| `irs_rcn/` | IRS "Active Fuel Refineries" (RCN) registry | US, 227 | 1 | yes | tax def (broader than crude); no capacity/coords → **OVERLAY ONLY, never merged** |

## How to add a source

1. `cp -r _template <name>` and edit `<name>/manifest.yml` (validate against
   `_schema/manifest.schema.json`).
2. Map every canonical field you can supply; leave the rest out.
3. If the format is nonstandard (nested JSON, GIS, multi-tab), implement `parse()` in
   `<name>/adapter.py` (see `_template/adapter.py`).
4. Set `source_tier` and `citable` honestly. GEM-authored ⇒ `citable: false`.
5. `python scripts/ingest.py --source <name>` and eyeball `canonical_summary.json`.
6. Record it in `docs/reference/source_roster.md`.

## Convention

- Raw downloads live in each source's `data/` (or the repo `data/`) and are **gitignored**.
- The manifest, `NOTES.md`, adapter, and `canonical_summary.json` are **committed** — the
  reproducible recipe, not the bytes.

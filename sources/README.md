# Background-source registry

Each background refinery dataset is registered here as `sources/<name>/manifest.yml`
(declarative column map + units + status/config maps + tier) plus an optional
`adapter.py` for nonstandard formats. `scripts/ingest.py` reads the manifest, normalizes
the source into the **canonical record** (`_schema/canonical_record.md`), and writes
`sources/<name>/canonical.parquet` (gitignored) + `canonical_summary.json` (committed).

**Adding a dataset is config, not engine code:** drop a manifest, run
`python scripts/ingest.py --source <name>`.

## Registered

| dir | source | tier | citable | notes |
|---|---|---|---|---|
| `rmi/` | RMI Refinery List (Feb '23) | 2 | no | primary global seed, ~800 rows |
| `ogj/` | OGJ Worldwide Refining survey | 2 | yes | dual-unit capacity; map JSON + PDF |
| `ogim/` | OGIM v2.7 refineries layer | 2 | no | GIS; location corroboration; data layer TBD |
| `china_rmi_tracker/` | GEM China Independent Oil Refinery Tracker | 2 | **no** | schema template + China seed; GEM-authored |

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

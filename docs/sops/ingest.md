# SOP — Ingest a background source

**Goal:** turn one registered background dataset into the canonical record schema so it can
be matched/merged. Greenfield step 1. Recipe: `workflows.md` §1.

## Steps

1. **Confirm the manifest** (`sources/<name>/manifest.yml`) is complete and validates
   against `sources/_schema/manifest.schema.json`. Every canonical field the source can
   supply is mapped; `source_tier` and `citable` are set honestly.
2. **Get the raw data local** into the manifest's `file_path` (gitignored). Drive files:
   download by `drive_file_id`. Sibling files (OGJ) are read in place via `sibling_path`.
3. **Run** `python scripts/ingest.py --source <name>`.
4. **Verify** `canonical_summary.json`:
   - row count matches expectation (RMI ≈ 800);
   - `with_coords` / `with_capacity_kbpd` fill rates are plausible;
   - **capacity units resolved correctly** — the #1 failure. Spot-check a few known
     refineries against `capacity_units.md`. A tonnes/万吨 source that came out 10× low or
     high means the unit mapping is wrong — fix the manifest, don't patch the data.
5. **Record** the source in `docs/reference/source_roster.md` if new.

## Gotchas

- **Sentinel zeros:** RMI uses `Design Capacity = 0` for unknown/idle. `to_kbpd` maps 0 →
  None (not a real 0 kbpd). Flag such rows for status research.
- **Coordinate order:** WKT `POINT(lon lat)` is lon-first; OGJ map `position` is `[lat,
  lon]`. The adapter handles OGJ; don't transpose RMI lat/lon.
- **`citable:false` sources** (RMI Typology Source, all GEM-authored): `source_url` is
  provenance only — it never becomes a `[ref]` without independent re-verification.
- **Custom formats** need `adapter.py` returning canonical-keyed rows; ingest applies the
  vocab maps + capacity normalization uniformly afterward.

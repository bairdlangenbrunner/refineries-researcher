# Staging workbook conventions

Every batch produces one xlsx under `batches/` (never overwrites; each build gets a fresh
timestamp). Baird reviews it and applies edits to the master manually.

## Filename

`batches/refineries_batch_<YYYYMMDD>_<HHMM>_ET[_<scope>]_<mode>.xlsx`

- Stamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`.
- `<mode>` is always present: `ingest` / `build` / `update` / `discovery` / `reconciliation`.
- `<scope>` (lowercase-hyphenated: `china`, `algeria`, `mena`) present whenever scoped.
- Triage and QC produce markdown memos, not xlsx: `batches/triage_<stamp>_ET.md`,
  `batches/qc_<stamp>_ET.md`.

## Sheets

Depends on mode; the leading sheet is always a **1:1 mirror of the relevant master rows**
in schema column order (see `gem_schema.md`), current values prefilled, with overlays only
on touched cells. Typical sheets:

- `master_mirror` / `<mode>_edits` — the rows to change, in schema order, `SheetRow`-keyed.
- `new_refineries` — proposed new records (discovery/build).
- `background_only` — background-dataset rows that didn't match the master (candidates to
  match to `OtherNames` first, then discover).
- `conflicts` — per-field disagreements between master and a background dataset.
- `entities` — new owners/parents needing an `entity_lookup.py` check.
- `qa` — flags, scope-boundary questions, unresolved items.

## Cell colors (per-cell source confidence)

Mirrors `confidence_tiers.md`:

- **green** — high (≥2 independent, or one primary).
- **yellow** — medium (single non-primary / single background dataset).
- **red** — low / conflict (prefer blank + `qa` note over staging).
- **blue** — re-verified unchanged.
- **green + empty** — staged deletion.

When adding a new sheet builder to `build_review_package.py`, also add its entry to the
`SHEET_DESCRIPTIONS` map so the workbook's first tab documents itself.

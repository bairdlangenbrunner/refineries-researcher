# Staging workbook conventions

Every batch produces one xlsx under `batches/` (never overwrites; each build gets a fresh
timestamp). Baird reviews it and applies edits to the main manually.

## Filename

`batches/refineries_batch_<YYYYMMDD>_<HHMM>_ET[_<scope>]_<mode>.xlsx`

- Stamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`.
- `<mode>` is always present: `ingest` / `build` / `update` / `discovery` / `reconciliation`.
- `<scope>` (lowercase-hyphenated: `china`, `algeria`, `mena`) present whenever scoped.
- Triage and QC produce markdown memos, not xlsx: `batches/triage_<stamp>_ET.md`,
  `batches/qc_<stamp>_ET.md`.

## Sheets

Depends on mode; the leading sheet is always a **1:1 mirror of the relevant main rows**
in schema column order (see `gem_schema.md`), current values prefilled, with overlays only
on touched cells.

**Do not emit the internal `RefineryID` (`R####`) column in review xlsx outputs.** It's an
internal crosswalk key (kept in `data/id_crosswalk.json` and the main parquet), not a
review field — Baird doesn't want it cluttering deliverables. Keep the source ID columns
(`rmi_refine_id`, `ogj_id`, `ogim_id`, `china_id`) and `SourcesPresent` for provenance.

Typical sheets:

- `main_mirror` / `<mode>_edits` — the rows to change, in schema order, `SheetRow`-keyed.
- `new_refineries` — proposed new records (discovery/build).
- `background_only` — background-dataset rows that didn't match the main (candidates to
  match to `OtherNames` first, then discover).
- `conflicts` — per-field disagreements between main and a background dataset.
- `entities` — new owners/parents needing an `entity_lookup.py` check.
- `qa` — flags, scope-boundary questions, unresolved items.

## Decision/Notes review columns (the feedback loop)

Every review sheet (possible pairs, under-merge candidates, reconciliation `Possible` /
`<source>_only` sheets) carries trailing `Decision` + `Notes` columns, blank for Baird.
Feedback rules:

- **Edit only `Decision` and `Notes`** — a wrong data value goes in `Notes`, never edited
  in place (the workbook is a mirror, not the main).
- **Blank `Decision` = not yet reviewed.** Partial passes are fine; hand the file back any
  time and unresolved rows carry into the regenerated workbook.
- **Keep the filename/stamp unchanged** so decisions map to the build they were made against.
- Controlled `Decision` vocab (lowercase):
  - pair/merge sheets (`PossiblePairs`, `Merge_candidates`): `merge` / `separate` / `unsure`.
  - reconciliation `Possible` sheets: `match` / `no match` / `unsure`.
  - reconciliation `<source>_only` sheets: `add` (genuine new refinery) / `match` (matches
    an existing main record — name it in `Notes`) / `out` (out of scope — say why) / `unsure`.
- Apply-back: Baird says "ingest decisions from `<file>`" → the agent parses the workbook,
  stages the decisions as committed JSON (audit trail), rebuilds the main, and regenerates
  fresh-stamped workbooks with decided rows dropped. Iterate until the sheets drain.

## Cell colors (per-cell source confidence)

Mirrors `confidence_tiers.md`:

- **green** — high (≥2 independent, or one primary).
- **yellow** — medium (single non-primary / single background dataset).
- **red** — low / conflict (prefer blank + `qa` note over staging).
- **blue** — re-verified unchanged.
- **green + empty** — staged deletion.

When adding a new sheet builder to `build_review_package.py`, also add its entry to the
`SHEET_DESCRIPTIONS` map so the workbook's first tab documents itself.

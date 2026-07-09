# SOP — Triage (plan the batch)

**Goal:** decide what to work on next. Output is a markdown memo, not a workbook. Recipe:
`workflows.md` §6.

## Inputs

- `data/master_*.parquet` (once it exists) — coverage by country, fill rates, staleness.
- `sources/*/canonical_summary.json` — what each background source still offers that the
  master lacks.
- Prior `conflicts`/`qa` items from build/reconciliation/QC.
- External sanity checks: EIA/JODI/OPEC country refining-capacity totals vs master totals.

## Produce

`batches/triage_<stamp>_ET.md`:
- top coverage gaps (countries under-represented vs known capacity);
- fields with the worst fill rate (what an Update sweep should target);
- unresolved conflicts and scope-boundary questions;
- a recommended next batch (workflow + scope) with rough size.

Greenfield note: early triage is mostly "ingest what's left, then build, then fill the
biggest countries first."

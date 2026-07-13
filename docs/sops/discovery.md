# SOP — Discover new refineries

**Goal:** find refineries missing from the main. Recipe: `workflows.md` §4.

## Where to look

- **Background-only rows** from build/reconciliation (RMI/OGJ/OGIM rows unmatched to the
  main). **Match to an existing record's `OtherNames` first** — most are renames, not
  misses. Only genuine misses become new records.
- **Coverage gaps:** countries/regions with few or zero main records vs known refining
  capacity (EIA/JODI country totals as a sanity check).
- **New-build pipeline:** announced `proposed`/`construction` refineries (trade press,
  operator announcements, government energy plans).
- **Revival:** `cancelled`/`retired` sites with new activity → a genuinely new project is a
  NEW record referencing the dead one in Notes, not an edit to the dead record.

## Bar to add a new record

Enough independent evidence to fill at minimum: name, country, approximate location,
status, and one capacity or owner data point — each with a verified `[ref]`. Below that,
stage to `qa` as a lead, not a record.

## Escalate

>5 candidate clusters in one country (systematic gap — discuss scope before generating
many records). Scope-boundary candidates (topping/mini plant, condensate splitter,
petrochem-only, bio/GTL) → get the ruling, log it in `controlled_vocab.md`.

## Output

`batches/refineries_batch_<stamp>_<scope>_discovery.xlsx` (`new_refineries` + `qa` sheets).

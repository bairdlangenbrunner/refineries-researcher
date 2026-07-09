# SOP — Quality control

**Goal:** audit data health. QC **detects**; Update **fixes**. Never edits data. Recipe:
`workflows.md` §7.

## Checks

- **Schema/vocab:** `Status`, `Configuration`, `Accuracy` values all in the controlled
  vocab (`controlled_vocab.md`); no stray casing.
- **`[ref]` integrity:** no orphan `[ref]` (ref filled, value blank) and no unsourced
  value (value filled, `[ref]` blank and not flagged estimated).
- **No GEM/abarrelfull URLs** anywhere in `[ref]` columns.
- **Capacity sanity:** `CapacityInKbpd` consistent with `Capacity`+`CapacityUnits`
  (re-run `capacity_normalize`); flag outliers (>1,500 kbpd, or a 10× gap between master
  and a source — the 万吨 trap signature).
- **Coordinates:** present, in range, on land near the stated country; flag lat/lon that
  look transposed.
- **Duplicates:** near-duplicate records (name + coords within ~1 km) → possible missed
  merge.
- **Link rot:** sample `[ref]` URLs through `url_verifier.py`.

## Output

`batches/qc_<stamp>_ET.md` (or an xlsx for large runs). Route fixes to an Update batch.
Escalate if >10% of sampled cells are unsupported (systemic issue).

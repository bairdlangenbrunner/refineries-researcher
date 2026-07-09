# SOP — Build / refresh the master

**Goal:** cluster the ingested canonical sources into one master record per physical
refinery, on the GEM schema. Greenfield step 2. Recipe: `workflows.md` §2.

## Steps

1. Ensure every source is ingested (`sources/<name>/canonical.parquet` exists).
2. Run `merge.py --sources rmi,ogj,china_rmi_tracker [,ogim]`. It:
   - clusters via `match.py` (country/ISO3 block → name + haversine + capacity score);
   - assigns stable `RefineryID`s (crosswalk committed so IDs survive rebuilds);
   - fills `rmi_refine_id` / `ogj_id` / `ogim_id` / `SourcesPresent`;
   - picks each field's value by tier + agreement; **routes disagreements to `conflicts`,
     never silently averages**;
   - normalizes capacity to `CapacityInKbpd`;
   - fills **no `[ref]` columns** (background URLs aren't verified GEM refs).
3. Review `batches/refineries_batch_<stamp>_build.xlsx`:
   - `background_only` rows: match to an existing cluster under `OtherNames` before
     accepting as a distinct refinery;
   - `conflicts`: material capacity/owner/status disagreements → queue for Update research;
   - singletons present in only one source: confirm they're real, not artifacts.
4. Baird applies the reviewed build to the master.

## Decisions to escalate

- Two sources disagree on >10% of matched rows (systematic — unit or vintage mismatch).
- A source contributes >30 unmatched rows in a country (coverage or matching problem).
- China overlap: use `china_rmi_tracker.Is_In_RMI_20230508` to pre-link to RMI; don't
  double-count.
- Clustering threshold tuning (name/distance/capacity weights) is a Baird call — log the
  chosen thresholds in this SOP once set.

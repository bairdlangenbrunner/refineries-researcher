# SOP — Build / refresh the main

**Goal:** cluster the ingested canonical sources into one main record per physical
refinery, on the GEM schema. Greenfield step 2. Recipe: `workflows.md` §2.

## Steps

1. Ensure every source is ingested (`sources/<name>/canonical.parquet` exists).
2. Run `merge.py --sources rmi,ogj,ogim,china_rmi_tracker,eia,india_ppac,brazil_anp,climate_trace`
   — the eight **mergeable** sources. `irs_rcn` is overlay-only (no capacity/coords) and is
   **never** passed to `--sources`; it is handled by reconciliation instead. It:
   - clusters via `match.py` (coord blocking → name + haversine + capacity; plus a
     country-blocked greedy-1:1 pass for coordless sources);
   - assigns stable `RefineryID`s (crosswalk committed so IDs survive rebuilds — a cluster
     containing any seed source keeps its existing id);
   - fills the per-source crosswalk ids (`rmi_refine_id`/`ogj_id`/`ogim_id`/`china_id`/
     `eia_id`/`climate_trace_id`/`india_ppac_id`/`brazil_anp_id`) + `SourcesPresent`;
   - picks each field's value by **per-field source priority** (`FIELD_PRIORITY` in
     `merge.py`); **routes disagreements to `conflicts`, never silently averages**;
   - normalizes capacity to `CapacityInKbpd`;
   - fills **no `[ref]` columns** (background URLs aren't verified GEM refs).
3. Export + review: `export_main.py` (worldwide xlsx) and `export_possible_review.py`
   (non-clustered `possible` pairs). Then:
   - `possible` pairs: confirm/reject; a confirmed one is an under-merge to fix (tune
     thresholds or add a name/capacity assignment);
   - `main_<stamp>.conflicts.parquet`: material capacity/owner/status/location
     disagreements → queue for Update research. Note climate_trace's nameplate capacity is
     deliberately last in priority, so its high figures surface here rather than being adopted;
   - singletons present in only one source: confirm they're real (e.g. climate_trace-only
     genuine misses like Dangote/Duqm/Olmeca), not artifacts.
4. Baird applies the reviewed build to the main.

## Per-field source priority (set in `merge.py:FIELD_PRIORITY`)

Every mergeable source must appear in a field's list to contribute that field (an omitted
source is silently dropped for it). Current rationale: Tier-1 gov sources rank first for
their own country (they only hold values there) — **EIA** for US capacity/status/owner,
**india_ppac**/**brazil_anp** for national capacity, **brazil_anp** for start year; **RMI**
is the global design-capacity backbone; **OGIM** is the location source; **climate_trace**
capacity is nameplate-max and sits **last** (fills genuine-miss rows only; overlaps → conflicts).
UPPERCASE-name sources (OGIM, EIA) sit late for `name` so they lose case ties.

## Decisions to escalate

- Two sources disagree on >10% of matched rows (systematic — unit or vintage mismatch).
- A source contributes >30 unmatched rows in a country (coverage or matching problem).
- China overlap: use `china_rmi_tracker.Is_In_RMI_20230508` to pre-link to RMI; don't
  double-count.
- Clustering threshold tuning (name/distance/capacity weights) is a Baird call — log the
  chosen thresholds in this SOP once set.

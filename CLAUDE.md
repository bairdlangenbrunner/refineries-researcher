# Refineries Researcher — operational guide

Backend scaffolding for an agentic research + reconciliation workflow that builds and
maintains **Global Energy Monitor's worldwide crude-oil refinery database** — a new,
open-access tracker (the *Global Oil Refinery Tracker*, working name **GORT**).

This project is **greenfield**: unlike the sibling LNG/pipeline researchers, there is
**no live GEM refineries backend yet**. The near-term job is to *build the initial
database* by ingesting several background datasets, de-duplicating them into one master
record set on GEM's schema, and researching the gaps. The medium-term job is the same
maintenance loop the siblings run (update / discover / reconcile / triage / QC).

Researcher initials in the tracker: **BL**. The agent **never overwrites a hand-curated
master by machine merge** and **never publishes** — every batch produces a reviewable
Excel deliverable + staged JSON that Baird reviews and applies to the master manually.

Where things live — **read on demand as the workflow dictates, not all at once**:

- **The GEM refinery schema** (authoritative for *what columns exist and what they mean*):
  `docs/reference/gem_schema.md` — derived from GEM's own *China Independent Oil Refinery
  Tracker for RMI* data dictionary, generalized worldwide.
- **Controlled vocabulary**: `docs/reference/controlled_vocab.md` (status, configuration,
  location accuracy). **Capacity units + conversions** (the `tttpa`/万吨 trap, Mt/a↔kbpd):
  `docs/reference/capacity_units.md`.
- **SOPs** (operational *how*): `docs/sops/` — `ingest.md` (background source → canonical),
  `build.md` (merge canonical sources → master), `discovery.md`, `update.md`,
  `reconciliation.md`, `triage.md`, `qc.md`.
- **Workflow recipes** (commands, in order): `docs/workflows.md`.
- **Background-dataset registry**: `sources/` — one `manifest.yml` (+ optional `adapter.py`)
  per dataset. RMI, OGJ, OGIM, and the GEM China tracker are registered. How to add one:
  `sources/README.md`.
- **Reference**: `docs/reference/` — `confidence_tiers.md`, `source_roster.md`,
  `workbook_conventions.md`; plus `docs/country_notes/`.
- **Full project context / pending items**: `docs/PROJECT_SETUP_AND_CONTEXT.md`.

---

## STANDING RULES — do not violate

1. **Never cite GEM as a source.** No gem.wiki, globalenergymonitor.org, or any GEM
   surface in `[ref]` columns or outputs. The China-tracker and any GEM-authored dataset
   are *seed data to reconcile*, **not** citable evidence. The goal is to surface what
   *other*, independent sources exist. (This applies to `abarrelfull.wikidot.com` echoes of
   GEM too — chase the primary source they footnote.)
2. **Never fabricate source URLs.** If a value can't be verified, describe the source
   precisely in `Notes` and mark it estimated/inferred (`EstimatedCapacity? = Yes`, etc.).
3. **Don't defend wrong findings.** Baird challenges data points actively. Acknowledge
   errors, revise on evidence, regenerate outputs.
4. **Corroborate with 2+ independent sources (near-requirement).** For any data point
   (status, capacity, configuration, ownership, start/retired year, location) try to find
   two *independent* sources that agree. 2+ independent → high; single non-primary →
   medium; single weak → low (prefer leaving blank + a Notes flag). The same wire story
   republished, mirrors of one document, and anything tracing back to GEM do NOT count as
   two. Record the tier + sources. Detail: `docs/reference/confidence_tiers.md`.
5. **A background dataset is one source in a conflict, never automatically authoritative.**
   RMI, OGJ, and OGIM disagree on capacity and coordinates constantly. Value
   disagreements route to normal source-search, not blind adoption of any one dataset.

---

## Scope of the database (what counts as a refinery)

- **In scope:** crude-oil refineries — facilities that distil/convert crude oil into
  refined petroleum products. Include condensate splitters that process field condensate
  into products. Capture the whole lifecycle: `proposed`, `construction`, `operating`,
  `idle`/`mothballed`, `retired`, `cancelled`, `shelved`.
- **Out of scope (for now):** standalone petrochemical plants with no crude distillation,
  biorefineries/biodiesel/renewable-diesel-only plants, GTL/CTL plants, LNG/gas processing
  (that's the LNG + pipeline trackers), and blending/storage terminals with no refining.
  A refinery's *associated* petrochemical units ARE captured, on the refinery record, in
  `PetchemFacilities`.
- **Threshold + edge cases** are still being set — when a candidate is ambiguous
  (topping plant, mini-refinery, mothballed-then-demolished), **flag it to Baird** rather
  than silently including/excluding. This is a greenfield decision surface; log the
  ruling in `docs/reference/controlled_vocab.md` once made.

---

## Workflow router

Read the relevant `docs/workflows.md` section + SOP before starting a batch.

| Workflow | Trigger phrases | Recipe + rules |
|---|---|---|
| **Ingest a background source** (greenfield) | "ingest RMI", "load the OGJ map", "pull OGIM refineries into canonical", "add a source" | `workflows.md` §1 + Ingest SOP |
| **Build/refresh the master** (greenfield) | "build the master", "merge the sources", "de-dup RMI vs OGJ", "rebuild the master database" | `workflows.md` §2 + Build SOP |
| **Update existing refineries** (maintenance) | "update refineries in <country>", "refresh <country>", "fill blank refs", "status sweep for <country>" | `workflows.md` §3 + Update SOP |
| **Discover new refineries** | "find new refineries in <country>", "discovery run", "what's missing in <country>" | `workflows.md` §4 + Discovery SOP |
| **Reconcile vs a background dataset** | "reconcile OGJ for <country>", "OGIM diff", "compare master to <dataset>" | `workflows.md` §5 + Reconciliation SOP |
| **Triage** (plan the batch; memo) | "what should we work on", "what's stale", "where are the gaps" | `workflows.md` §6 + Triage SOP; output is a markdown memo |
| **Quality control** (xlsx; detects → Update fixes) | "qc pass", "data-health audit", "link-rot sweep" | `workflows.md` §7 + QC SOP; memo/xlsx, never edits live data |

Routing notes:
- In the greenfield phase the common path is **Ingest → Build → Discovery/Update**.
  Reconciliation is the same engine as Build's cross-source match, run against a *single*
  dataset once the master exists.
- A background-only row (present in RMI/OGJ/OGIM but not the master) is usually **not** a
  new refinery — **match it to an existing master record under another name first** (→
  `OtherNames`); only genuine misses become new records.
- QC never edits: it audits and routes fixes to Update ("QC detects, Update fixes").

---

## Sourcing is pluggable (the RMI/OGJ/OGIM registry)

There is **no single canonical reference** for refineries. Each background dataset is
registered under `sources/<name>/` as a declarative `manifest.yml` (column maps, units,
status map, `source_tier`, ID field) + an optional `adapter.py` for custom parsing.
`scripts/ingest.py` normalizes any source into one **canonical schema**
(`sources/_schema/canonical_record.md`); `scripts/match.py` + `scripts/merge.py` then run
the hybrid (name + country + coordinate-distance + capacity) match to build/refresh the
master. **Adding a dataset is config, not engine code** — drop a new manifest and run
`ingest.py --source <name>`.

Registered sources (full detail in `docs/reference/source_roster.md`):
- **rmi** — RMI Refinery List (Feb '23), ~800 rows worldwide. Primary global seed. Tier 2.
- **ogj** — Oil & Gas Journal Worldwide Refining survey (map JSON + PDF). Dual-unit
  capacity (kbbl/cd + Mt/a), owner, status. Tier 2 (industry-standard).
- **ogim** — OGIM v2.7 refineries layer (GIS). Location/coordinate corroboration. Tier 2.
- **china_rmi_tracker** — GEM's own China Independent Oil Refinery Tracker for RMI.
  **Schema template + China seed** — but GEM-authored, so **seed data, never a citation.**
- **irs_rcn** — IRS "Active Fuel Refineries" (Refiner Control Number) registry, US-only, Tier 1
  primary gov source. ⚠ Tax definition (§4101), broader than crude-only — ~half is gas/NGL/
  biodiesel/LNG/petchem. No capacity/coords → never auto-matches. **RULING (Baird): OVERLAY
  ONLY — keep it registered + ingested, but NEVER merge into the master.** Its sole use is the
  US reconciliation/discovery review workbook (`batches/refineries_irs_reconciliation_*.xlsx`);
  crude candidates are worked by hand, out-of-scope rows stay flagged.

---

## Hard requirements (override anything below)

- **The agent never publishes and never machine-overwrites the curated master.** Output
  is a staging xlsx + staged JSON; Baird applies edits to the master manually.
- **Every URL passes `scripts/url_verifier.py` before going in the xlsx** — even URLs that
  worked in prior batches, even URLs inherited from RMI/OGJ. Verification means the
  specific claimed value (capacity, owner, status, year, coords) appears on that page.
  Reject GEM URLs and `abarrelfull.wikidot.com` (chase its footnote instead).
- **No orphan `[ref]` cells** — never fill a `[ref]` without a paired data value, and never
  leave a researched value without a `[ref]` (except genuinely estimated values, which get
  `EstimatedCapacity? = Yes` / a Notes flag instead of a fabricated URL).
- **Capacity is always normalized to `CapacityInKbpd`** alongside the source's original
  `Capacity` + `CapacityUnits`. Watch the unit traps: `Mt/a` (metric tonnes/yr) ≈ 20.08
  kbpd; the Chinese `tttpa`/`万吨` unit = 10,000 t/yr (NOT 1,000). See `capacity_units.md`.
  Never convert a tonnes-based capacity without confirming which tonnes unit it is.
- **Don't create duplicate entities** — run `scripts/entity_lookup.py` before staging a new
  owner/parent. Entities are shared across all GEM trackers; a refiner may already exist.
- **Never auto-adopt a background value.** A match/reconciliation finding is a *candidate*
  for research, not an applied value. A single Tier-2 dataset never reaches "high" alone.
- **Coordinates:** keep the source's own lat/lon + `Accuracy` (exact/approximate). When
  two sources disagree by more than ~1 km, treat it as a conflict to resolve, not a
  rounding difference. WKT `POINT(lon lat)` is lon-first — do not transpose.

---

## Controlled vocabulary (locked — full table in `controlled_vocab.md`)

- **`Status` (lowercase):** `proposed`, `construction`, `operating`, `idle`, `mothballed`,
  `retired`, `cancelled`, `shelved`.
- **`Configuration` (lowercase):** `topping`, `hydroskimming`, `medium conversion`,
  `deep conversion`. RMI's single-letter codes map: **H → hydroskimming, M → medium
  conversion, D → deep conversion** (RMI has no `topping` code).
- **`Accuracy`:** `exact`, `approximate`.
- When in doubt, copy the exact casing from `controlled_vocab.md`; don't invent values.

---

## When to escalate to the user

- A background dataset disagrees with the master on >10% of matched rows (material
  capacity/owner/status conflicts), or a source produces >30 background-only rows in one
  country that don't match existing records.
- A whole class of values looks systematically wrong (schema/unit misunderstanding, not a
  finding) — especially a suspected tonnes-unit mislabel.
- Discovery surfaces >5 candidate clusters in one country.
- A candidate sits on a scope boundary (topping plant, condensate splitter, petrochem-only,
  bio/GTL) — get the ruling before staging, and record it in `controlled_vocab.md`.
- A QC spot-check shows >10% of sampled cells unsupported.

---

## Common commands

```bash
python scripts/ingest.py --source rmi   --out sources/rmi/canonical.parquet
python scripts/ingest.py --source ogj   --out sources/ogj/canonical.parquet
python scripts/match.py   --against master --source ogj --out batches/staging/match_ogj/
python scripts/merge.py   --sources rmi,ogj,ogim,china_rmi_tracker --out data/master_<stamp>.parquet
python scripts/export_master.py                 # latest master -> batches/refineries_master_<stamp>_worldwide_export.xlsx (drops RefineryID)
python scripts/export_possible_review.py        # latest master's possible pairs -> batches/refineries_possible_review_<stamp>.xlsx
python scripts/build_review_package.py --staging batches/staging/<run>/ \
    --output batches/refineries_batch_<stamp>_<scope>_<mode>.xlsx   # <stamp>: TZ=America/New_York date "+%Y%m%d_%H%M_ET"
pip install -r requirements.txt
```

## When starting a new task

1. Confirm the scope (country/region, and for reconciliation the `--source`) and whether
   you're in the greenfield (Ingest/Build) or maintenance (Update/Discover) phase.
2. Read the relevant `docs/workflows.md` section + SOP.
3. Load the master with the loader in `scripts/paths.py`; never work from a stale export.
4. Run the pre-delivery checks (`docs/sops/qc.md`) before presenting.

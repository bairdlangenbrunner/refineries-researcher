# Project setup & context

## What this is

Backend scaffolding for building and maintaining GEM's worldwide crude-oil refinery
database (working name **GORT — Global Oil Refinery Tracker**). Sibling of the
`lng-terminals-researcher`, `lng-carriers-researcher`, and `pipelines-researcher` repos and
built to the same conventions, but **greenfield**: there is no live GEM refineries backend
yet, so the first job is assembling the initial database from background datasets.

Researcher: Baird Langenbrunner (initials **BL**). The agent never publishes and never
machine-overwrites the curated master — it produces reviewable xlsx + staged JSON that
Baird applies by hand.

## The greenfield pipeline

```
   background sources ──ingest.py──▶ canonical parquets ──merge.py──▶ master ──▶ Update/Discover/QC
   (rmi, ogj, ogim,                  (one schema)         (GEM schema,
    china_rmi_tracker)                                     RefineryIDs)
```

1. **Ingest** each source to the canonical schema (done for the format; run per source).
2. **Build** the master by clustering across sources (`merge.py`/`match.py` — skeletons).
3. **Update / Discover / Reconcile / QC** — ongoing maintenance, same as the siblings.

## Background sources (see `docs/reference/source_roster.md`)

- **RMI Refinery List (Feb '23)** — ~800 rows, primary seed. Drive folder
  `1gJaJ7KYByNAHzoF0ve6ienuEvsfP28bV`, file `15CoiFuiT-JtDD-cb3ZV-Cx_Qb8RUPiDk`.
- **OGJ Worldwide Refining survey** — map JSON + PDF in `../refineries-tracker/`.
- **OGIM v2.7** — refineries GIS layer; docs at `/Users/baird/Dropbox/_gis-data/ogim/`,
  data layer still to be added.
- **GEM China Independent Oil Refinery Tracker for RMI** — the schema template + China
  seed; Google Sheet `1PyNUtGUDLdY1chJ-MkzzgV_OnAcNTp2QlIq8jLhStPw`. GEM-authored → seed
  only, never citable.

## Open decisions (greenfield surface — get Baird's ruling, then log it)

- **Scope boundaries:** condensate splitters, topping/mini refineries, associated-vs-
  standalone petrochemical, bio/GTL/CTL exclusion edge cases → `controlled_vocab.md`
  "Scope-boundary rulings".
- **Match thresholds** for `merge.py` clustering (name/distance/capacity weights) →
  `sops/build.md`.
- **Entity source** for `entity_lookup.py` until a live backend exists (union of master +
  `../gem-database-access/` exports?).
- **Tracker name/abbrev** (GORT is a working name) and eventual publication surface.
- **Capacity basis:** nameplate/design (RMI) vs distillation vs throughput — decide the
  master's canonical basis and note conversions.

## Status of the build (update as it evolves)

- ✅ Repo scaffold, schema, controlled vocab, capacity conversions, source registry + 4
  manifests, ingest engine, OGJ adapter.
- ⛏ `match.py` / `merge.py` / `entity_lookup.py` / `url_verifier.py` /
  `build_review_package.py` — skeletons to port from the sibling repos.
- ☐ Download raw sources locally and run the first ingest.
- ☐ First master build + review.

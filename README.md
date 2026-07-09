# refineries-researcher

Backend scaffolding for building and maintaining **Global Energy Monitor's worldwide
crude-oil refinery database** (working name **GORT — Global Oil Refinery Tracker**). Sibling
of `lng-terminals-researcher`, `lng-carriers-researcher`, and `pipelines-researcher`; same
conventions, but **greenfield** — the first job is assembling the initial database from
several background datasets, then maintaining it.

The agent never publishes and never machine-overwrites the curated master. Every batch
produces a reviewable Excel deliverable + staged JSON that the researcher applies by hand.

## Layout

```
CLAUDE.md                     operational guide (read this first)
docs/
  workflows.md                command recipes per workflow
  sops/                       ingest, build, update, discovery, reconciliation, triage, qc
  reference/                  gem_schema, controlled_vocab, capacity_units,
                              confidence_tiers, source_roster, workbook_conventions
  country_notes/              per-country findings
  PROJECT_SETUP_AND_CONTEXT.md
sources/                      pluggable background-dataset registry (rmi, ogj, ogim,
                              china_rmi_tracker) — manifest.yml (+ adapter.py) each
scripts/                      ingest / match / merge / entity_lookup / url_verifier /
                              build_review_package (+ paths, capacity_normalize)
data/                         master_*.parquet + gitignored raw downloads
batches/                      xlsx deliverables + staging/
tests/
```

## Quick start

```bash
pip install -r requirements.txt
python scripts/capacity_normalize.py            # self-check the unit conversions
python scripts/ingest.py --source rmi           # (after downloading the RMI xlsx locally)
```

## The four background sources

| Source | Role | Citable? |
|---|---|---|
| RMI Refinery List (Feb '23) | primary global seed (~800) | no |
| OGJ Worldwide Refining survey | capacity/status corroboration (dual units) | yes* |
| OGIM v2.7 refineries layer | location corroboration (GIS) | no |
| GEM China Independent Oil Refinery Tracker | schema template + China seed | **no** |

\* every URL still passes `url_verifier.py` before it can be a `[ref]`; GEM/gem.wiki and
`abarrelfull.wikidot.com` are never citable. See `docs/reference/source_roster.md`.

## Status

Scaffold + schema + capacity engine + source registry + ingest are in place. `match.py`,
`merge.py`, `entity_lookup.py`, `url_verifier.py`, and `build_review_package.py` are
skeletons to port from the sibling repos. See `docs/PROJECT_SETUP_AND_CONTEXT.md`.

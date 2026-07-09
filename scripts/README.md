# scripts/

Engine + helpers. Import `paths` for the schema/paths and `capacity_normalize` for units;
don't re-derive either inline.

| Script | Status | Purpose |
|---|---|---|
| `paths.py` | ✅ done | Canonical paths + master schema column order (`SCHEMA`, `ordered_columns`, `latest_master`) + controlled vocab lists. |
| `capacity_normalize.py` | ✅ done | Capacity → kbpd. Handles the `Mt/a` and 万吨/`tttpa` traps. Run it directly for the self-check. |
| `ingest.py` | ✅ works | Background source → canonical parquet via `sources/<name>/manifest.yml` (+ adapter). Greenfield step 1. |
| `match.py` | ⛏ skeleton | Hybrid refinery matcher (country block + name + haversine + capacity). Used by build & reconciliation. |
| `merge.py` | ⛏ skeleton | Cluster matched sources → one master record per refinery on the GEM schema. Greenfield step 2. |
| `entity_lookup.py` | ⛏ skeleton | De-dup owners/parents against shared GEM entities before staging. |
| `url_verifier.py` | ⛏ skeleton | Confirm a URL contains the claimed value; blocks gem.wiki/abarrelfull. Host-block logic is live. |
| `build_review_package.py` | ⛏ skeleton | Staged JSON → reviewable xlsx (colors = confidence). |

## Typical invocation order (greenfield)

```bash
# 1. ingest each source to canonical
python scripts/ingest.py --source rmi
python scripts/ingest.py --source ogj
python scripts/ingest.py --source china_rmi_tracker
# python scripts/ingest.py --source ogim        # after the OGIM data layer is added

# 2. build the master by clustering across sources
python scripts/merge.py --sources rmi,ogj,china_rmi_tracker --out data/master_<stamp>.parquet

# 3. thereafter: match a single source vs master for reconciliation
python scripts/match.py --source ogj --against master --out batches/staging/match_ogj/
```

## Building out the skeletons

The four ⛏ skeletons have working siblings in `../lng-terminals-researcher/scripts/` and
`../pipelines-researcher/scripts/` — same patterns (staging JSON, confidence colors,
`[ref]` GUARD, entity dedup). Refineries are **point features**, so `match.py` geometry is
a plain haversine, not route overlap. Port + adapt rather than writing from scratch.

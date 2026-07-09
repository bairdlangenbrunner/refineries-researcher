"""Match a canonical source against the master (or another source) — SKELETON.

    python scripts/match.py --source ogj --against master --out batches/staging/match_ogj/

Hybrid refinery matcher: block by country/ISO3, then score candidate pairs on
  - name similarity (token-set ratio; strip "Refinery"/owner boilerplate first)
  - coordinate distance (haversine; <1 km strong, 1-5 km possible, >25 km reject)
  - capacity_kbpd proximity (ratio within ~15% corroborates)
Emit: matched pairs (with per-field agree/conflict), source-only rows, master-only rows.

Used by BOTH build (cross-source dedup) and reconciliation (single source vs master).
See docs/sops/build.md and docs/sops/reconciliation.md.

TODO: implement. Reuse the LNG/pipeline matcher patterns (../pipelines-researcher/
scripts/match.py) — refineries are point features, so geometry is a simple haversine,
not route overlap. Watch: WKT is lon-first; OGJ position is [lat, lon].
"""

from __future__ import annotations
import argparse
from math import radians, sin, cos, asin, sqrt


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--against", default="master")
    ap.add_argument("--out", required=True)
    ap.parse_args()
    raise NotImplementedError("match.py is a skeleton — see the module docstring.")


if __name__ == "__main__":
    main()

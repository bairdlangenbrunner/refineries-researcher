"""Build/refresh the master from matched canonical sources — SKELETON.

    python scripts/merge.py --sources rmi,ogj,ogim,china_rmi_tracker --out data/master_<stamp>.parquet

Greenfield step 2. Runs match.py pairwise to cluster the same physical refinery across
sources, then for each cluster emits ONE master record on the GEM schema (paths.SCHEMA):
  - RefineryID assigned (R0001…), stable across rebuilds via a committed id crosswalk.
  - crosswalk ids (rmi_refine_id/ogj_id/ogim_id) + SourcesPresent filled.
  - per field, pick the best source value by tier + agreement; DISAGREEMENTS are NOT
    silently resolved — they go to a conflicts report for research, value left as the
    higher-tier one with a Notes flag.
  - capacity normalized to CapacityInKbpd via capacity_normalize.
  - NO [ref] columns filled here (background URLs aren't verified GEM refs) — Update fills
    those. `citable:false` sources never contribute a URL at all.

Output: data/master_<stamp>.parquet + a build report (cluster count, singletons per
source, conflict count) + batches/refineries_batch_<stamp>_build.xlsx for review.

See docs/sops/build.md. TODO: implement on top of match.py.
"""

from __future__ import annotations
import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True, help="comma-separated source names")
    ap.add_argument("--out", required=True)
    ap.parse_args()
    raise NotImplementedError("merge.py is a skeleton — see the module docstring.")


if __name__ == "__main__":
    main()

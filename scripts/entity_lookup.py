"""Check whether an owner/parent entity already exists before staging a new one — SKELETON.

    python scripts/entity_lookup.py "Sonatrach"

Entities (companies) are shared across ALL GEM trackers. Before staging a new Owner/Parent,
check for an existing canonical entity so we don't create duplicates (a refiner very often
already exists via the oil/gas/LNG trackers). A match anywhere = reuse the existing name.

TODO: implement against the shared GEM entity source. Until GORT has a live backend, the
practical check is a fuzzy lookup over the union of Owner/Parent names already in the
master + the other GEM tracker exports in ../gem-database-access/. Reuse
../pipelines-researcher/scripts/entity_lookup.py once the entity source is decided.
"""

from __future__ import annotations
import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--country", help="annotate matches only; NEVER the sole filter")
    ap.parse_args()
    raise NotImplementedError("entity_lookup.py is a skeleton — see the docstring.")


if __name__ == "__main__":
    main()

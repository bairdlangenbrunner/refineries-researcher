"""Build the staging xlsx deliverable from staged JSON — SKELETON.

    python scripts/build_review_package.py --staging batches/staging/<run>/ \
        --output batches/refineries_batch_<stamp>_<scope>_<mode>.xlsx

Turns the agent's staged edits/new-records JSON into the reviewable workbook Baird applies
by hand. Conventions (sheets, filename, per-cell confidence colors) live in
docs/reference/workbook_conventions.md — keep this script and that doc in lockstep.

Rules baked in:
  - leading sheet mirrors the master rows in paths.SCHEMA column order, current values
    prefilled, overlays only on touched cells.
  - cell color = confidence tier (green/yellow/red/blue; green+empty = deletion).
  - GUARD: a URL may only land in a [ref] column; refuse URLs aimed at value columns.
  - GUARD: every URL must carry a url_verifier pass flag; unverified URLs don't ship.
  - never overwrite an existing batch file — each build gets a fresh timestamp.
  - maintain the SHEET_DESCRIPTIONS map so the first tab is self-documenting.

TODO: implement with openpyxl. Reuse ../lng-terminals-researcher/scripts/
build_review_package.py as the base (same color semantics, same [ref] GUARD).
"""

from __future__ import annotations
import argparse

SHEET_DESCRIPTIONS = {
    "readme": "What each sheet is and what the cell colors mean.",
    "master_mirror": "Rows to change, in schema order, SheetRow-keyed; overlays on touched cells.",
    "new_refineries": "Proposed new records (discovery/build).",
    "background_only": "Background-dataset rows not matched to the master — match to OtherNames first.",
    "conflicts": "Per-field disagreements between master and a background dataset.",
    "entities": "New owners/parents needing an entity_lookup check.",
    "qa": "Flags, scope-boundary questions, unresolved items.",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", required=True)
    ap.add_argument("--output", required=True)
    ap.parse_args()
    raise NotImplementedError("build_review_package.py is a skeleton — see the docstring.")


if __name__ == "__main__":
    main()

"""Canonical paths + the master schema column order.

Import this instead of hard-coding paths or column offsets anywhere else. The GEM schema
(docs/reference/gem_schema.md) is the source of truth for meanings; this file is the
machine-readable column order the workbook builder and master loader agree on.
"""

from __future__ import annotations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
SOURCES = REPO / "sources"
BATCHES = REPO / "batches"
STAGING = BATCHES / "staging"

# Sibling GEM repos root (this repo lives under _github-repos-gem/refineries-researcher)
GEM_REPOS = REPO.parent


# --- Master schema (see docs/reference/gem_schema.md) -------------------------------
# Value columns and their [ref] partners, in emit order. `None` = no [ref] partner.
SCHEMA: list[tuple[str, str | None]] = [
    ("RefineryID", None),
    ("RefineryName", None),
    ("OtherNames", None),
    ("Country", None),
    ("ISO3", None),
    ("Subnational", None),
    ("Status", "Status [ref]"),
    ("Owner", "Ownership [ref]"),
    ("Parent", "Ownership [ref]"),
    ("Capacity", "Capacity [ref]"),
    ("CapacityUnits", None),
    ("CapacityInKbpd", None),
    ("EstimatedCapacity?", None),
    ("Configuration", "Configuration [ref]"),
    ("NelsonComplexity", None),
    ("StartYear", "StartYear [ref]"),
    ("RetiredYear", "RetiredYear [ref]"),
    ("City", None),
    ("Latitude", "Location [ref]"),
    ("Longitude", "Location [ref]"),
    ("Accuracy", None),
    ("Feedstock", "Feedstock [ref]"),
    ("FeedstockNotes", None),
    ("PetchemFacilities", "PetrochemFacility [ref]"),
    ("CapacityUtilization", "CapacityUtilization [ref]"),
    ("CapacityUtilizationYear", None),
    ("rmi_refine_id", None),
    ("ogj_id", None),
    ("ogim_id", None),
    ("china_id", None),
    ("SourcesPresent", None),
    ("InScope", None),          # superset-first: yes | no | unknown (default at build)
    ("ScopeReason", None),      # why in/out of scope, filled by the separate scope pass
    ("Wiki", None),
    ("Notes1", None),
    ("Notes2", None),
    ("Notes3", None),
    ("Notes4", None),
]

# Per-source crosswalk id column on the master (source name -> master column)
SOURCE_ID_COLUMN = {
    "rmi": "rmi_refine_id",
    "ogj": "ogj_id",
    "ogim": "ogim_id",
    "china_rmi_tracker": "china_id",
}

STATUS_VOCAB = [
    "proposed", "construction", "operating", "idle",
    "mothballed", "retired", "shelved", "cancelled",
]
CONFIGURATION_VOCAB = ["topping", "hydroskimming", "medium conversion", "deep conversion"]
ACCURACY_VOCAB = ["exact", "approximate"]


def ordered_columns() -> list[str]:
    """Full flat column list in emit order, deduping shared [ref] columns."""
    cols: list[str] = []
    for value_col, ref_col in SCHEMA:
        cols.append(value_col)
        if ref_col and ref_col not in cols:
            cols.append(ref_col)
    return cols


def latest_master() -> Path | None:
    """Most recent data/master_*.parquet, or None if the master doesn't exist yet."""
    candidates = sorted(DATA.glob("master_*.parquet"))
    return candidates[-1] if candidates else None

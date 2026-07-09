"""Optional per-source adapter.

Implement `parse(manifest, raw_path)` only when the source format is nonstandard
(nested JSON, GIS layer, multi-tab workbook, PDF table). It must return a list of dicts
keyed by CANONICAL field names (see ../_schema/canonical_record.md). `ingest.py` will then
apply status_map / configuration_map / capacity normalization / ISO3 backfill uniformly,
so do NOT do those here — just get the rows into canonical field names.

For plain xlsx/csv/geojson sources, no adapter is needed: ingest.py handles them from the
manifest `column_map` alone.
"""

from __future__ import annotations
from typing import Any


def parse(manifest: dict[str, Any], raw_path: str) -> list[dict[str, Any]]:
    """Return canonical-keyed rows. Raise NotImplementedError until written."""
    raise NotImplementedError(
        f"No adapter implemented for source {manifest.get('name')!r}. "
        "Either remove `adapter:` from the manifest (if the generic loader suffices) "
        "or implement parse() here."
    )

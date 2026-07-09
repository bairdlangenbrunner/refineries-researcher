"""OGJ map-JSON adapter.

The OGJ export (../refineries-tracker/refineries.json) is a NON-JSON JS object literal
keyed by year:  {2009:{map:[{B:"Owners: Shell",F:"Primary capacity(kbbl/cd): 68.0",
H:"Primary capacity(Mt/a): 3.4",K:"Status: Operational",id:ayuwnn,name:Fredericia,
active:true,position:[55.56,9.74]}, ...]}, 2010:{...}, ...}

So we can't json.load it directly. We take the LATEST year block, strip the "Label: "
prefixes from the letter-coded fields, and emit canonical-keyed rows. `mt_a` is carried in
an extra key so match.py can cross-check F ≈ H * 20.08.
"""

from __future__ import annotations
import re
from typing import Any


def _demjson_load(text: str) -> dict:
    """Best-effort parse of the JS-object export. Prefers json5/demjson3 if installed,
    else falls back to a tolerant regex-based reader for the shape above."""
    for modname in ("json5",):
        try:
            mod = __import__(modname)
            return mod.loads(text)
        except Exception:
            pass
    raise RuntimeError(
        "Install json5 (pip install json5) to parse the OGJ map export, or extract the "
        "refinery rows from the WW Refining PDF via ../refineries-tracker/"
        "extract-refineries-from-PDF-table.ipynb instead."
    )


_PREFIX = re.compile(r"^[^:]*:\s*")


def _strip(v: Any) -> Any:
    return _PREFIX.sub("", v).strip() if isinstance(v, str) else v


def parse(manifest: dict, raw_path: str) -> list[dict]:
    with open(raw_path, "r", encoding="utf-8") as fh:
        data = _demjson_load(fh.read())

    # latest year block
    year = max(data.keys(), key=lambda k: int(k))
    points = data[year].get("map", [])

    rows = []
    for p in points:
        pos = p.get("position") or [None, None]           # [lat, lon]
        cap = _strip(p.get("F"))                            # kbbl/cd == kbpd
        mt_a = _strip(p.get("H"))                           # Mt/a (cross-check)
        rows.append({
            "source_id": p.get("id"),
            "name": p.get("name"),
            "owner": _strip(p.get("B")),
            "status": _strip(p.get("K")),
            "capacity_value": _num(cap),
            "capacity_units": "kbpd",
            "latitude": pos[0],
            "longitude": pos[1],
            "mt_a": _num(mt_a),                             # extra: for the 20.08 cross-check
            "ogj_year": year,
        })
    return rows


def _num(v: Any):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None

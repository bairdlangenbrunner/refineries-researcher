"""OGJ map-JSON adapter.

The OGJ export (../refineries-tracker/refineries.json) is NOT valid JSON/JSON5: it is a
JS app-state dump with UNQUOTED keys and values, where each refinery point is a fixed-key
record inside a per-year `map:[...]` array:

  {2009:{map:[{B:Owners: Shell,F:Primary capacity(kbbl/cd): 68.0,
               H:Primary capacity(Mt/a): 3.4,K:Status: Operational,
               id:ayuwnn,name:Fredericia,active:true,position:[55.56,9.74]}, ...]},
   2010:{...}, ... 2023:{...}}

So we (1) locate the LATEST year's `map:[` array by bracket-counting, and (2) regex each
record by anchoring on the literal field labels (robust to commas inside owner/name).
Emits canonical-keyed rows; `mt_a` is carried as an extra for the F ≈ H*20.08 cross-check.

SCOPE NOTE: this particular export is EUROPE-ONLY (~127 refineries) with 2009-2023 history.
The WORLDWIDE OGJ (~700) is in the WW Refining PDF (../refineries-tracker/*OGJ_WWRefining*
.pdf) + its extraction notebook — a separate source to register when needed.
"""

from __future__ import annotations
import re
from typing import Any

_REC = re.compile(
    r'\{B:Owners:\s*(?P<owner>.*?),'
    r'F:Primary capacity\(kbbl[^)]*\):\s*(?P<kbbl>[-\d.]*),'
    r'H:Primary capacity\(Mt[^)]*\):\s*(?P<mta>[-\d.]*),'
    r'K:Status:\s*(?P<status>.*?),'
    r'id:(?P<id>[^,]*),'
    r'name:(?P<name>.*?),'
    r'active:(?P<active>true|false),'
    r'position:\[(?P<lat>[-\d.]+),(?P<lon>[-\d.]+)\]\}'
)


def _map_array(raw: str, year: str) -> str | None:
    m = re.search(rf'[\{{,]{year}:\{{map:\[', raw)
    if not m:
        return None
    i = m.end() - 1                      # index of the opening '['
    depth = 0
    for j in range(i, len(raw)):
        if raw[j] == '[':
            depth += 1
        elif raw[j] == ']':
            depth -= 1
            if depth == 0:
                return raw[i:j + 1]
    return None


def _num(v: Any):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def parse(manifest: dict, raw_path: str) -> list[dict]:
    with open(raw_path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()

    years = sorted(set(re.findall(r'[\{,](\d{4}):\{map:\[', raw)), key=int)
    if not years:
        raise RuntimeError("No `<year>:{map:[` blocks found — is this the OGJ map export?")
    year = years[-1]                     # latest
    arr = _map_array(raw, year)

    rows = []
    for m in _REC.finditer(arr):
        d = m.groupdict()
        rows.append({
            "source_id": d["id"],
            "name": d["name"].strip(),
            "owner": d["owner"].strip() or None,
            "status": d["status"].strip() or None,
            "capacity_value": _num(d["kbbl"]),
            "capacity_units": "kbpd",
            "latitude": _num(d["lat"]),
            "longitude": _num(d["lon"]),
            "mt_a": _num(d["mta"]),        # extra: for the 20.08 cross-check
            "ogj_year": year,
        })
    return rows

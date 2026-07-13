"""India PPAC "Installed Refining Capacity" adapter.

Source: Petroleum Planning & Analysis Cell (PPAC), an attached office of India's Ministry
of Petroleum & Natural Gas — the official government compiler of India refinery capacity
(figures reported by the oil companies). Single-sheet xlsx, capacity as of 1 April 2025.
US-equivalent authority for India: primary government registry, citable (not a GEM surface).

⚠ UNIT: capacity is in **'000 MT** (thousand metric tonnes/year of crude), NOT MMTPA and
NOT barrels — the adapter emits capacity_units='kt/a' and lets capacity_normalize handle it
(kt/a x 0.02008 = kbpd). Panipat 15000 ('000 MT) = 15.0 MMTPA ≈ 301 kbpd.

Layout gotchas the adapter handles:
  - rows 1-4 are blank/title/units; header is row 5 (0-idx 4); data rows 6-28 (0-idx 5-27).
  - the COMPANY column is VERTICALLY MERGED per operator, so only the first refinery of each
    block carries the company — forward-fill it down.
  - drop the 'ALL INDIA TOTAL' row and the 'Source:'/footnote rows.
  - the REFINERIES cell is '<operator abbrev>, <location>' (e.g. 'IOC, Digboi') -> name =
    location, owner = full company. Cauvery Basin is shown at 0 (under augmentation) -> its
    capacity normalizes to null, not a real zero.
  - STATE has dirty cells: 'IOC, Paradip' state = '\nODISHA' (strip); CPCL rows say 'CHENNAI'
    (a city; PPAC error for Tamil Nadu) — kept verbatim (stripped), not silently rewritten.

No coordinates and no status column in this file.
"""

from __future__ import annotations

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    raise SystemExit("india_ppac adapter needs pandas + openpyxl (pip install -r requirements.txt)")

HEADER_ROW = 4          # 0-indexed row holding COMPANY | REFINERIES | STATE | <date>
SKIP_NAMES = {"all india total", "refineries"}


def _clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).replace("\n", " ").strip()
    return s or None


def parse(manifest: dict, raw_path: str) -> list[dict]:
    raw = pd.read_excel(raw_path, sheet_name=0, header=None)
    src_url = (manifest.get("location") or {}).get("url")

    # columns 1..4 are COMPANY, REFINERIES, STATE, capacity (col 0 is an empty margin)
    out = []
    company = None
    seq = 0
    for i in range(HEADER_ROW + 1, len(raw)):
        comp = _clean(raw.iat[i, 1])
        refinery = _clean(raw.iat[i, 2])
        state = _clean(raw.iat[i, 3])
        cap = raw.iat[i, 4]
        if comp:
            company = comp                       # forward-fill merged company block
        if not refinery or refinery.lower() in SKIP_NAMES:
            continue                             # total row / stray
        # 'IOC, Digboi' / 'CPCL,Manali' / 'RPL (SEZ), Jamnagar' -> location after first comma
        if "," in refinery:
            _, loc = refinery.split(",", 1)
        else:
            loc = refinery
        name = loc.strip().rstrip("*").strip() or refinery

        try:
            cap_val = float(cap)
        except (TypeError, ValueError):
            cap_val = None

        seq += 1
        out.append({
            "source_id": f"PPAC-{seq:02d}",
            "name": name,
            "owner": company,
            "country": "India",
            "iso3": "IND",
            "subnational": state,
            "city": name,                        # PPAC gives no separate city; location doubles as it
            "latitude": None,
            "longitude": None,
            "capacity_value": cap_val,           # '000 MT/yr
            "capacity_units": "kt/a",
            "status": None,                      # no status column; Cauvery Basin flagged via 0 capacity
            "configuration": None,
            "start_year": None,
            "source_url": src_url,
        })
    return out

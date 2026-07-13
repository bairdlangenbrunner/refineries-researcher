"""Refinery capacity unit normalization → kbpd (thousand barrels/calendar-day).

Single source of truth for the conversions documented in
docs/reference/capacity_units.md. Import `to_kbpd`; do not re-derive factors inline.

Key facts:
  - crude ≈ 7.33 bbl per metric tonne  ->  1 Mt/a = 1e6 * 7.33 / 365 = 20.08 kbpd
  - the Chinese unit 万吨/a ("tttpa" in GEM's China tracker) = 10,000 t/yr, NOT 1,000.
    So 万吨/a = 0.01 Mt/a -> 0.2008 kbpd. (750 万吨/a = 150.6 kbpd — matches GEM's value.)
"""

from __future__ import annotations

BBL_PER_TONNE = 7.33
KBPD_PER_MTPA = BBL_PER_TONNE * 1_000_000 / 365 / 1000  # ≈ 20.082
BBL_PER_M3 = 6.28981                                    # 1 m³ = 6.28981 bbl (1 bbl = 0.158987 m³)

# Normalize unit strings to a canonical key. Extend as new source labels appear.
_UNIT_ALIASES = {
    "bpd": "bpd", "b/d": "bpd", "bbl/day": "bpd", "bbl/d": "bpd", "barrels/day": "bpd",
    "kbpd": "kbpd", "kb/d": "kbpd", "kbbl/cd": "kbpd", "kbbl/d": "kbpd",
    "mt/a": "Mt/a", "mtpa": "Mt/a", "mt/y": "Mt/a", "mt/yr": "Mt/a",
    "万吨/a": "wan_t/a", "万吨/年": "wan_t/a", "wan_t/a": "wan_t/a", "tttpa": "wan_t/a",
    "t/a": "t/a", "tpa": "t/a", "t/yr": "t/a", "tonnes/year": "t/a",
    # thousand tonnes/year (India PPAC publishes '000 MT)
    "kt/a": "kt/a", "kt/yr": "kt/a", "kt/y": "kt/a", "kilotonnes/year": "kt/a",
    "'000mt": "kt/a", "000mt": "kt/a", "'000mt/a": "kt/a", "thousandmt": "kt/a",
    # volume/day (Brazil ANP reports crude throughput in m³/day; also m³/year)
    "m3/d": "m3/d", "m³/d": "m3/d", "m3/dia": "m3/d", "m³/dia": "m3/d",
    "m3/day": "m3/d", "m³/day": "m3/d",
    "m3/a": "m3/a", "m³/a": "m3/a", "m3/ano": "m3/a", "m³/ano": "m3/a", "m3/yr": "m3/a",
}

# Multiplier from canonical unit -> kbpd
_TO_KBPD = {
    "bpd": 1 / 1000,
    "kbpd": 1.0,
    "Mt/a": KBPD_PER_MTPA,
    "wan_t/a": KBPD_PER_MTPA / 100,   # 万吨 = 1e4 t = 0.01 Mt
    "kt/a": KBPD_PER_MTPA / 1000,     # 1e3 t = 0.001 Mt  (India PPAC '000 MT)
    "t/a": KBPD_PER_MTPA / 1_000_000,
    "m3/d": BBL_PER_M3 / 1000,        # m³/day -> kbpd
    "m3/a": BBL_PER_M3 / 365 / 1000,  # m³/year -> kbpd
}


class UnknownUnit(ValueError):
    pass


def canonical_unit(units: str) -> str:
    key = (units or "").strip().lower().replace(" ", "")
    # keep the CJK 万吨 forms (lower() is a no-op on them) — re-check raw too
    if key in _UNIT_ALIASES:
        return _UNIT_ALIASES[key]
    raw = (units or "").strip()
    if raw in _UNIT_ALIASES:
        return _UNIT_ALIASES[raw]
    raise UnknownUnit(f"Unrecognized capacity unit: {units!r}")


def to_kbpd(value: float | None, units: str) -> float | None:
    """Convert a capacity value in `units` to kbpd. None or <=0 -> None.

    Capacity is strictly positive, so any non-positive value is an unknown/idle
    sentinel, not a real 0 kbpd: RMI uses 0, OGIM uses -999.
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v <= 0:                      # 0 (RMI) / -999 (OGIM) etc. == unknown/idle sentinel
        return None
    return round(v * _TO_KBPD[canonical_unit(units)], 3)


if __name__ == "__main__":
    # quick self-check against known data points
    checks = [
        (350000, "bpd", 350.0),        # RMI Skikda
        (750, "tttpa", 150.6),         # GEM China Dongming: 750 万吨/a
        (3.4, "Mt/a", 68.28),          # OGJ Fredericia (~68 kbbl/cd)
        (106.4, "kbpd", 106.4),        # already kbpd
        (69000, "m3/d", 434.0),        # Brazil REPLAN/Paulínia ~69,000 m³/d ≈ 434 kbpd
    ]
    for val, unit, expect in checks:
        got = to_kbpd(val, unit)
        flag = "ok" if abs(got - expect) < 0.5 else "MISMATCH"
        print(f"{val} {unit:>6} -> {got} kbpd (expect ~{expect}) [{flag}]")

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

# Normalize unit strings to a canonical key. Extend as new source labels appear.
_UNIT_ALIASES = {
    "bpd": "bpd", "b/d": "bpd", "bbl/day": "bpd", "bbl/d": "bpd", "barrels/day": "bpd",
    "kbpd": "kbpd", "kb/d": "kbpd", "kbbl/cd": "kbpd", "kbbl/d": "kbpd",
    "mt/a": "Mt/a", "mtpa": "Mt/a", "mt/y": "Mt/a", "mt/yr": "Mt/a",
    "万吨/a": "wan_t/a", "万吨/年": "wan_t/a", "wan_t/a": "wan_t/a", "tttpa": "wan_t/a",
    "t/a": "t/a", "tpa": "t/a", "t/yr": "t/a", "tonnes/year": "t/a",
}

# Multiplier from canonical unit -> kbpd
_TO_KBPD = {
    "bpd": 1 / 1000,
    "kbpd": 1.0,
    "Mt/a": KBPD_PER_MTPA,
    "wan_t/a": KBPD_PER_MTPA / 100,   # 万吨 = 1e4 t = 0.01 Mt
    "t/a": KBPD_PER_MTPA / 1_000_000,
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
    """Convert a capacity value in `units` to kbpd. None/0 -> None (0 == unknown sentinel)."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v == 0:                      # RMI et al. use 0 for unknown/idle; not a real 0 kbpd
        return None
    return round(v * _TO_KBPD[canonical_unit(units)], 3)


if __name__ == "__main__":
    # quick self-check against known data points
    checks = [
        (350000, "bpd", 350.0),        # RMI Skikda
        (750, "tttpa", 150.6),         # GEM China Dongming: 750 万吨/a
        (3.4, "Mt/a", 68.28),          # OGJ Fredericia (~68 kbbl/cd)
        (106.4, "kbpd", 106.4),        # already kbpd
    ]
    for val, unit, expect in checks:
        got = to_kbpd(val, unit)
        flag = "ok" if abs(got - expect) < 0.5 else "MISMATCH"
        print(f"{val} {unit:>6} -> {got} kbpd (expect ~{expect}) [{flag}]")

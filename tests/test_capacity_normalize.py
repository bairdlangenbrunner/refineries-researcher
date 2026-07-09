"""Tests for capacity unit normalization — the highest-risk domain math."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from capacity_normalize import to_kbpd, canonical_unit, UnknownUnit  # noqa: E402

import pytest  # noqa: E402


def test_bpd():
    assert to_kbpd(350000, "bpd") == 350.0
    assert to_kbpd(350000, "bbl/day") == 350.0


def test_kbpd_passthrough():
    assert to_kbpd(106.4, "kbpd") == 106.4
    assert to_kbpd(68.0, "kbbl/cd") == 68.0


def test_mtpa():
    # 1 Mt/a ≈ 20.08 kbpd (7.33 bbl/tonne)
    assert to_kbpd(1, "Mt/a") == pytest.approx(20.08, abs=0.05)
    assert to_kbpd(3.4, "Mtpa") == pytest.approx(68.28, abs=0.1)


def test_wan_tonne_trap():
    """The 万吨/tttpa trap: 10,000 t/yr, NOT 1,000. 750 -> ~150.6 kbpd (not ~15)."""
    assert to_kbpd(750, "tttpa") == pytest.approx(150.6, abs=0.2)
    assert to_kbpd(750, "万吨/a") == pytest.approx(150.6, abs=0.2)
    # a thousand-tonne misread would give ~15 — guard against regressing to it
    assert to_kbpd(750, "tttpa") > 100


def test_zero_is_unknown():
    # RMI uses 0 for unknown/idle — not a real 0 kbpd
    assert to_kbpd(0, "bpd") is None


def test_none():
    assert to_kbpd(None, "bpd") is None
    assert to_kbpd("", "Mt/a") is None


def test_unknown_unit():
    with pytest.raises(UnknownUnit):
        to_kbpd(100, "furlongs")


def test_canonical_unit_aliases():
    assert canonical_unit("kbbl/cd") == "kbpd"
    assert canonical_unit("Mtpa") == "Mt/a"
    assert canonical_unit("tttpa") == "wan_t/a"

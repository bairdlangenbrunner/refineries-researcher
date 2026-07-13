# Capacity units & conversions

Refinery capacity is quoted in several units across the background sources. The main
always stores the **original** value + units (`Capacity`, `CapacityUnits`) **and** a
normalized `CapacityInKbpd`. `scripts/capacity_normalize.py` is the single source of truth
for the math — import it, don't re-derive conversions inline.

## Canonical unit: kbpd

`kbpd` = thousand barrels per calendar day. All comparison, ranking, and reconciliation
happen in kbpd.

## Units seen in the sources

| Unit string | Meaning | → kbpd |
|---|---|---|
| `bpd`, `bbl/day`, `b/d` | barrels/day | ÷ 1,000 |
| `kbpd`, `kbbl/cd`, `kb/d` | thousand barrels/day | ×1 (already canonical) |
| `Mt/a`, `Mtpa`, `Mt/y` | **million metric tonnes**/year of crude | × **20.08** |
| `万吨/a`, `万吨/年`, `tttpa` | **10,000 metric tonnes**/year (Chinese unit) | × **0.2008** |
| `t/a`, `tpa` | metric tonnes/year | × 2.008e-5 |
| `m3/d`, `m³/dia` | cubic metres/day (Brazil ANP) | × **6.290** ÷ 1,000 |
| `m3/a`, `m³/ano` | cubic metres/year | × 6.290 ÷ 365 ÷ 1,000 |

### The tonnes→barrels factor

Crude oil averages ≈ **7.33 barrels per metric tonne** (API/density-dependent; 7.33 is the
conventional refinery-throughput figure). So:

```
1 Mt/a = 1,000,000 t/yr × 7.33 bbl/t ÷ 365 d = 20,082 bbl/d ≈ 20.08 kbpd
```

Cross-check against the OGJ map JSON, which carries both units: Fredericia 68.0 kbbl/cd /
3.4 Mt/a = 20.0; Kalundborg 106.4 / 5.3 = 20.08. The data uses ~20.0–20.08; we use
**20.08** (7.33 bbl/t) as the default and note OGJ's own per-record ratio when it differs.

### ⚠ The `tttpa` / 万吨 trap (do not get this wrong)

In GEM's China Independent Oil Refinery Tracker, Chinese capacities are logged as
`tttpa`. This is **NOT** "thousand tonnes per annum" — it is 万吨/年 (**wàn dūn**,
10,000 tonnes/year). Worked example from that tracker: Shandong Dongming `750 tttpa` →
`150.75 kbpd`. Check: 750 × 10,000 t = 7.5 Mt/a → 7.5 × 20.08 = **150.6 kbpd** ✓
(matches). If you read `tttpa` as thousand-tonnes you get 15 kbpd — a **10× error**.

Rule: any Chinese-sourced refinery capacity in "万吨" or a `tttpa`-style label is
10,000-tonne units. When `CapacityUnits` is ambiguous on a tonnes basis, **confirm the
unit before converting** and flag it in `Notes`. This is the single most common capacity
error in refinery data — escalate a whole class of suspicious tonnes values to Baird.

### Volume vs mass units

Brazil's ANP reports refining capacity as a **volume rate** (m³/day or bbl/day), not a mass
rate, so no density assumption is needed — `1 m³ = 6.28981 bbl` is exact. Do **not** apply the
7.33 bbl/tonne factor to a cubic-metre figure. India's PPAC reports **MMTPA** (million tonnes/
year of crude) → use the `Mt/a` conversion (×20.08). Keep each source's native unit in
`CapacityUnits` and let `capacity_normalize.to_kbpd` do the conversion.

## Estimated capacity

When a capacity is inferred (e.g. summed unit capacities, or a dated figure carried
forward), set `EstimatedCapacity? = Yes` and explain in `Notes` — do not fabricate a
`Capacity [ref]`.

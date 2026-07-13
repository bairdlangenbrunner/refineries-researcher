"""Brazil ANP refinery-capacity adapter — Anuário Estatístico Table 2.29.

Source: ANP (Agência Nacional do Petróleo, Gás Natural e Biocombustíveis — Brazil's
petroleum regulator), "Capacidade de refino" table from the Anuário Estatístico 2025
(dados abertos CSV), nominal capacity as of 31/12/2024. Brazil-only national anchor;
primary regulator source, citable (federal open data, Decreto 8.777/2016). Not a GEM surface.

CSV specifics: UTF-8 (BOM) — read `utf-8-sig`; `;`-separated; comma decimal (`decimal=','`).
Columns (verbatim PT):
  REFINARIA           — refinery name (operator is implicit in the name; NO separate column)
  MUNICÍPIO (UF)      — 'Paulínia (SP)' -> city 'Paulínia', state 'SP'
  INÍCIO DE OPERAÇÃO  — start year
  CAPACIDADE NOMINAL  — nominal capacity in BARRELS PER DAY (not m³) -> units 'bpd', /1000 = kbpd

19 clean data rows, no total/footnote rows in the CSV. Two names carry trailing footnote
digits ('Rnest - Refinaria Abreu e Lima1', 'Paraná Xisto2') — stripped. No coordinates and no
status column. ⚠ 'Paraná Xisto' is Petrobras' SIX oil-SHALE (xisto) plant, capacity 0 crude
bbl/d (its throughput is measured in tonnes of shale) — a scope-boundary case (unconventional,
not crude distillation): emitted with null capacity and flagged for a Baird ruling, not
silently dropped.
"""

from __future__ import annotations
import re

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    raise SystemExit("brazil_anp adapter needs pandas (pip install -r requirements.txt)")

COL_NAME = "REFINARIA"
COL_MUN = "MUNICÍPIO (UF)"
COL_START = "INÍCIO DE OPERAÇÃO"
COL_CAP = "CAPACIDADE NOMINAL"
_MUN_UF = re.compile(r"^(.*?)\s*\(([A-Z]{2})\)\s*$")


def _clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s or None


def parse(manifest: dict, raw_path: str) -> list[dict]:
    df = pd.read_csv(raw_path, sep=";", encoding="utf-8-sig", decimal=",")
    src_url = (manifest.get("location") or {}).get("url")

    out = []
    for i, r in df.iterrows():
        raw_name = _clean(r.get(COL_NAME))
        if not raw_name:
            continue
        name = re.sub(r"\d+$", "", raw_name).strip()   # drop trailing footnote digit

        city = state = None
        mun = _clean(r.get(COL_MUN))
        if mun:
            m = _MUN_UF.match(mun)
            city, state = (m.group(1).strip(), m.group(2)) if m else (mun, None)

        try:
            start = int(r.get(COL_START))
        except (TypeError, ValueError):
            start = None
        try:
            cap = float(r.get(COL_CAP))
        except (TypeError, ValueError):
            cap = None

        out.append({
            "source_id": f"ANP-{i + 1:02d}",
            "name": name,
            "owner": None,                       # ANP capacity table has no operator column
            "country": "Brazil",
            "iso3": "BRA",
            "subnational": state,
            "city": city,
            "latitude": None,
            "longitude": None,
            "capacity_value": cap,               # barrels/day (0 for Paraná Xisto shale -> null kbpd)
            "capacity_units": "bpd",
            "status": None,                      # no status column
            "configuration": None,
            "start_year": start,
            "source_url": src_url,
        })
    return out

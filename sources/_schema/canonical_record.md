# Canonical record schema

`scripts/ingest.py` normalizes every background source into this flat canonical shape
before matching/merging. It is deliberately a **subset** of the full GEM schema
(`docs/reference/gem_schema.md`) — only the fields any background source can supply, plus
provenance. Research-only fields (`[ref]` columns, feedstock, utilization, notes) are
filled later during Update/Discovery, not at ingest.

| Canonical field | Type | Notes |
|---|---|---|
| `source` | str | Source name, e.g. `rmi`, `ogj`, `ogim`. |
| `source_id` | str | The source's own primary key (RMI `rmi_refine_id`, etc.). |
| `name` | str | Refinery name as given by the source. |
| `country` | str | Country (source spelling; normalized against ISO3 where possible). |
| `iso3` | str | ISO 3166-1 alpha-3, if present or derivable. |
| `subnational` | str | State/province, if present. |
| `city` | str | City/town, if present. |
| `latitude` | float | WGS84 decimal degrees. |
| `longitude` | float | WGS84 decimal degrees. |
| `capacity_value` | float | Capacity in the source's original units. |
| `capacity_units` | str | Original units (`bpd`, `Mt/a`, `万吨/a`, …). |
| `capacity_kbpd` | float | Normalized by `capacity_normalize.py`. |
| `status` | str | Mapped to the controlled `Status` vocab via the manifest `status_map`. |
| `owner` | str | Owner/operator, if present. |
| `configuration` | str | Mapped to the controlled `Configuration` vocab (RMI H/M/D → …). |
| `start_year` | int | If present. |
| `source_url` | str | The source's own cited URL, if any. **Provenance only — NOT auto-promoted to a GEM `[ref]`** (must be re-verified first; reject GEM/abarrelfull). |
| `source_tier` | int | From the manifest. |

Missing fields are left null. `ingest.py` writes one parquet per source at
`sources/<name>/canonical.parquet` (gitignored) plus a small committed
`sources/<name>/canonical_summary.json` (row count, per-column fill rate) for audit.

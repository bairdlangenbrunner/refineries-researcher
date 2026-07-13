# GEM Refinery schema (Global Oil Refinery Tracker — working name GORT)

Authoritative column list + meaning for the main refinery database. Derived from GEM's
own **China Independent Oil Refinery Tracker for RMI** data dictionary and generalized
worldwide (China-only fields dropped; lifecycle statuses and source-crosswalk fields
added). This is the schema the staging xlsx and `data/main_*.parquet` conform to.

Every substantive field is **`[ref]`-paired**: the value column holds a value, the paired
`… [ref]` column holds one or more corroborating URLs (space- or newline-separated). Never
fill a value without its `[ref]`, and never fill a `[ref]` without a value (estimated
values excepted — see `EstimatedCapacity?`). `[ref]` cells never hold GEM/gem.wiki URLs.

## Column groups

### Identity
| Column | Meaning |
|---|---|
| `RefineryID` | GEM-assigned unique ID (e.g. `R0001`). Assigned at Build time; stable thereafter. |
| `RefineryName` | Canonical English name. Prefer `<Owner/Operator> <Place> Refinery`. |
| `OtherNames` | Alternate/legacy/local names, `;`-separated. Where background-only rows get matched. |
| `Country` | Country name (English, GEM spelling). |
| `ISO3` | ISO 3166-1 alpha-3 code (e.g. `USA`, `CHN`, `DZA`). |
| `Subnational` | State / province / region. |

### Status (lifecycle)
| Column | Meaning |
|---|---|
| `Status` | One of: `proposed`, `construction`, `operating`, `idle`, `mothballed`, `retired`, `cancelled`, `shelved`. See `controlled_vocab.md`. |
| `Status [ref]` | Corroboration for status. |

### Ownership
| Column | Meaning |
|---|---|
| `Owner` | Direct lowest-level owner(s), `;`-separated. Often == operator. Run `entity_lookup.py` before adding a new one. |
| `Parent` | Parent company(ies) of the owner(s), `;`-separated. |
| `Ownership [ref]` | Corroboration for owner + parent. |

### Capacity
| Column | Meaning |
|---|---|
| `Capacity` | Value in the ORIGINAL units the reference used. Do not convert in place. |
| `CapacityUnits` | Units of `Capacity`: `bpd`, `kbpd`, `Mt/a`, `万吨/a` (10,000 t/yr), `bbl/day`. See `capacity_units.md`. |
| `CapacityInKbpd` | Capacity normalized to thousand barrels/day. **Always populated** when `Capacity` is. |
| `EstimatedCapacity?` | `Yes`/`No`. If `Yes`, `Capacity [ref]` may be blank; explain in `Notes`. |
| `Capacity [ref]` | Corroboration for capacity. |

### Configuration / complexity
| Column | Meaning |
|---|---|
| `Configuration` | `topping`, `hydroskimming`, `medium conversion`, `deep conversion`. RMI codes: H→hydroskimming, M→medium conversion, D→deep conversion. |
| `Configuration [ref]` | Corroboration. |
| `NelsonComplexity` | Nelson Complexity Index (optional; OGJ sometimes carries it). |

### Dates
| Column | Meaning |
|---|---|
| `StartYear` | Year first started operating. |
| `StartYear [ref]` | Corroboration. |
| `RetiredYear` | Year retired/closed, if applicable. |
| `RetiredYear [ref]` | Corroboration. |

### Location
| Column | Meaning |
|---|---|
| `City` | City/town. |
| `Latitude` | Decimal degrees, WGS84 (EPSG:4326). |
| `Longitude` | Decimal degrees, WGS84. |
| `Accuracy` | `exact` or `approximate`. |
| `Location [ref]` | Corroboration for coordinates. |

> WKT in source files is `POINT(longitude latitude)` — **lon first**. Don't transpose.

### Process
| Column | Meaning |
|---|---|
| `Feedstock` | Crude/other feedstock type(s), `;`-separated. |
| `FeedstockNotes` | Free text on feedstock. |
| `Feedstock [ref]` | Corroboration. |
| `PetchemFacilities` | Associated petrochemical units on-site (NOT standalone petchem plants). |
| `PetrochemFacility [ref]` | Corroboration. |

### Utilization
| Column | Meaning |
|---|---|
| `CapacityUtilization` | Percent of capacity used in a given year. |
| `CapacityUtilizationYear` | Year of that estimate. |
| `CapacityUtilization [ref]` | Corroboration. |

### Provenance / crosswalk (greenfield build fields)
| Column | Meaning |
|---|---|
| `rmi_refine_id` | Matched RMI `rmi_refine_id`, if any. |
| `ogj_id` | Matched OGJ record id, if any. |
| `ogim_id` | Matched OGIM feature id, if any. |
| `SourcesPresent` | Which background sources contain this refinery, e.g. `rmi;ogj;ogim`. |
| `Wiki` | gem.wiki page slug (internal only — NEVER used as a `[ref]`). |

### Notes
| Column | Meaning |
|---|---|
| `Notes1`..`Notes4` | Freeform: flags for later research, capture gaps, notable features, scope-boundary rulings. |

## Column order

The build script emits columns in the order above (Identity → Status → Ownership →
Capacity → Configuration → Dates → Location → Process → Utilization → Provenance → Notes),
with each `[ref]` column immediately following its value column. `scripts/paths.py` holds
the canonical ordered list — import it, don't hard-code offsets.

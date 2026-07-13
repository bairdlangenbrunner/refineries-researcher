# Controlled vocabulary

Locked value sets for the enumerated columns. Copy casing exactly; don't invent values.
New values require a Baird decision — record the ruling here when made.

## `Status` (lowercase)

Lifecycle of the refinery. Distinct from the LNG/pipeline trackers only in that refineries
add `idle`/`mothballed` for temporary shutdowns.

| Value | Meaning |
|---|---|
| `proposed` | Announced/planned; no construction. |
| `construction` | Under construction. |
| `operating` | In operation (incl. partial). |
| `idle` | Temporarily shut, expected to restart. |
| `mothballed` | Indefinitely shut, preserved, could restart. |
| `retired` | Permanently closed. |
| `shelved` | Development paused indefinitely (pre-construction). |
| `cancelled` | Project abandoned; will not be built. |

> The China tracker used only `operating`/`mothballed`/`retired` (existing plants). The
> worldwide tracker covers the full pipeline, so `proposed`/`construction`/`shelved`/
> `cancelled` are in play for new-build research.

## `Configuration` (lowercase)

Process complexity, simplest → most complex:

| Value | Meaning | RMI code |
|---|---|---|
| `topping` | Atmospheric distillation only (+ maybe naphtha reforming). | *(none)* |
| `hydroskimming` | Topping + reforming + hydrotreating; no conversion units. | `H` |
| `medium conversion` | Adds catalytic/thermal cracking (FCC/coker). | `M` |
| `deep conversion` | Adds hydrocracking/full residue conversion. | `D` |

RMI's `Refinery Type` column uses single letters **H / M / D** → map as above. RMI has no
`topping` code; a genuine topping plant identified in research is `topping`.

## `Accuracy` (lowercase)

Coordinate precision: `exact` | `approximate`.

## Scope-boundary rulings (append as decided)

Log here every ambiguous inclusion/exclusion ruling so it's consistent across batches
(see CLAUDE.md "Scope of the database"). Format: `<date> — <case> — <ruling> — <rationale>`.

- 2026-07-13 — asphalt refineries that distil crude (e.g. Talley Asphalt, Kern CA, 1.7 kbpd
  in EIA) — **IN SCOPE** (keep) — they run atmospheric crude distillation, so they are crude
  refineries regardless of small size or asphalt-heavy product slate. Small size alone is not
  an exclusion. (Standalone asphalt *blending/oxidizing* plants with no crude distillation stay
  out, same rule as petchem-only sites.)
- 2026-07-13 — EIA downstream-only sites with no atmospheric crude distillation (petchem/lube/
  NGL: Equistar Channelview, Excel Paralubes, Trecora, Pasadena Performance, Enterprise & Targa
  Mont Belvieu) — **OUT OF SCOPE** — no crude distillation = not a crude refinery. The eia
  adapter excludes them at ingest.
- 2026-07-13 — oil-shale refineries (e.g. Paraná Xisto / Petrobras SIX, São Mateus do Sul PR,
  in OGIM + ANP) — **IN SCOPE** (keep) — ruling (Baird): GRT is "an ALL refinery tracker", not
  only crude oil. Facilities that refine a hydrocarbon feed into refined products belong in the
  database even when the feed is not conventional crude. Sets the precedent for other shale/
  unconventional refineries (Estonia, Jordan). ⚠ Broader consequence flagged to Baird: this
  intent likely also pulls in GTL/CTL/bio-refineries that the CLAUDE.md scope section currently
  lists as out — pending an explicit ruling before that section is rewritten.
- 2026-07-13 — **GTL (gas-to-liquids), CTL (coal-to-liquids), and bio-refineries** (biodiesel/
  renewable-diesel/HVO) — **IN SCOPE** (keep) — ruling (Baird): confirms the all-refinery intent
  of the oil-shale ruling above. GRT tracks any facility that refines a hydrocarbon feed into
  refined products; feed type (crude / condensate / shale / gas / coal / bio) is **not** an
  exclusion criterion. CLAUDE.md "Scope of the database" rewritten accordingly. Still out:
  standalone petrochemical plants with no refining, LNG/gas *processing*, and blending/storage
  terminals. (Consequence: expect new candidate classes — Sasol Secunda/Oryx GTL, Shenhua &
  other China CTL, worldwide biodiesel/HVO plants — in future discovery.)

# Confidence tiers

Every staged value carries a confidence tier, driven by how many *independent* sources
corroborate it. This maps to the cell color in the staging xlsx (see
`workbook_conventions.md`).

| Tier | Rule | Cell color |
|---|---|---|
| **high** | ≥2 independent sources agree, OR one primary/regulatory source (company report, regulator filing). | green |
| **medium** | One credible non-primary source (trade press, a single background dataset). | yellow |
| **low** | One weak source, or inferred/estimated. Prefer leaving the value blank + a `Notes` flag over staging a low value. | red |
| **unchanged** | Re-verified against sources, value confirmed, no change. | blue |

## What counts as independent

Two sources are independent only if they are genuinely different origins:

- **NOT independent:** the same wire story republished; two mirrors/host-variants of one
  document; a primary source + its own press release echo; any two things that both trace
  back to GEM; a background dataset + `abarrelfull.wikidot.com` (which itself echoes
  OGJ/GEM).
- **A single background dataset (RMI, OGJ, OGIM) is one source → medium at best.** Two
  *different* background datasets that agree (e.g. RMI + OGJ) can reach high, but confirm
  they aren't both derived from the same OGJ survey first.

## Estimated / inferred values

Summed unit capacities, dated figures carried forward, or coordinate centroids are
`low`/estimated: set the relevant estimate flag (`EstimatedCapacity? = Yes`), explain in
`Notes`, and do **not** fabricate a `[ref]`.

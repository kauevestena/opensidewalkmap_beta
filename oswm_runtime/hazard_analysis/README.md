# OSWM Hazard Analysis

Hazard Analysis is a static, evidence-based webmap that identifies conditions
which may be uncomfortable, unfavorable, dangerous, or critical for different
pedestrians. It shares normalized evidence and longitudinal slope estimates
with the routing module, but keeps hazard severity separate from routing grade.

## Interpretation

The module is a screening and prioritization tool, not an accessibility
certificate. A severity of zero means **no rule matched the available
evidence**; it does not mean that a feature is safe. Missing tags remain
unknown and may produce `insufficient_data`.

The five levels are:

| Level | Label | Meaning |
|---:|---|---|
| 0 | No detected hazard | No rule matched known evidence |
| 1 | Uncomfortable | Additional effort or reduced comfort |
| 2 | Unfavorable | Meaningful accessibility degradation |
| 3 | Dangerous | Serious safety or mobility concern |
| 4 | Critical | Apparent barrier or extreme contextual risk |

Critical results include a separate `traversability` field so an impassable
barrier is not confused with a technically passable but extremely risky
condition.

## Profiles and categories

The profiles are general pedestrian, wheelchair user, blind/low-vision
pedestrian, and older/reduced-mobility pedestrian. Rules cover:

- longitudinal slope, separately for each travel direction;
- explicit `incline:across=*` cross slope;
- kerb transitions;
- tactile and material-transition detectability;
- surface smoothness and provisional material proxies;
- explicit barriers.

Rules are plain dictionaries in [`rules.py`](rules.py). They are provisional
and should be calibrated with affected users and accessibility specialists.
Surface material has deliberately lower confidence than direct smoothness
evidence. A missing tactile tag is never interpreted as `tactile_paving=no`.

Kerb and tactile values are paired by the same nearby transition record.
This prevents a flush kerb at one end of a crossing from being falsely paired
with absent tactile paving recorded at the opposite end. The uniform-surface
proxy is emitted only when crossing, kerb, and adjacent sidewalk surfaces are
all explicitly mapped and equal.

## Global terrain source

The default source hierarchy is:

1. numeric OSM `incline=*` for a network feature;
2. Copernicus DEM GLO-30 Public (2021) Cloud Optimized GeoTIFFs from the AWS
   Open Data Registry;
3. Copernicus DEM GLO-90 (2021) from AWS when a public GLO-30 tile is absent;
4. unknown.

Both AWS buckets are public and require no AWS account. Tiles are cached in
`.cache/oswm/elevation/`. GLO-30 is not quite complete because a small set of
30 m tiles has not been publicly released; GLO-90 supplies worldwide land
coverage for those cells.

Copernicus DEM is a **digital surface model**, including vegetation and built
structures. Its slope is low-confidence terrain context—not surveyed sidewalk
grade. The optional raster is therefore titled *Terrain difficulty potential*.
It is unsigned, smoothed for contextual display, and never used to infer cross
slope. Numeric OSM incline remains authoritative.

The generated metadata carries the required Copernicus attribution and source
URL. Node configuration lives in `ELEVATION_CONFIG` and
`HAZARD_TERRAIN_CONFIG` in the node's `config.py`.

## Shared generation

`generation/routing_demo_gen.py` produces routing and hazard artifacts in one
pass. Each network feature is normalized once, receives one cached slope
estimate, and is then evaluated by both policies. Outputs are written
atomically and parsed again before replacing the previous files.

Generated files:

| File | Purpose |
|---|---|
| `data/hazard_analysis/profiles.json` | Public profiles, levels, categories, explanations, and rule effects |
| `data/hazard_analysis/metadata.json` | Ruleset hash, generation audit, and warnings |
| `data/hazard_analysis/features_<profile>.geojson` | One lazy-loaded feature collection per profile |
| `data/hazard_analysis/terrain.json` | Raster bounds, source, licence, attribution, and thresholds |
| `data/hazard_analysis/terrain_<profile>.png` | Optional transparent terrain-potential image |

Profile GeoJSON and terrain PNG files are generated deployment artifacts and
can remain Git-ignored. The daily Pages workflow generates them before
publishing the node.

## Calibration workflow

1. Change only the policy dictionaries in `rules.py`.
2. Increment `HAZARD_RULESET_VERSION`.
3. Run the hazard and routing test suites.
4. Generate a representative node and inspect the profile audit.
5. Review samples with affected user groups.
6. Record the calibration basis before propagating the codebase version.

The deterministic ruleset hash makes every generated result traceable to the
exact policy used.

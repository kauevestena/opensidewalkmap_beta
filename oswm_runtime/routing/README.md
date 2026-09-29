# OSWM accessibility-aware routing

This directory contains the static browser router and the policy used to grade
pedestrian-network edges for different users. It is intentionally split into a
human-editable policy layer and a generic implementation layer.

## Status

The distance-only profile is a neutral baseline. The wheelchair,
blind/low-vision and elderly profiles are **provisional**: they recover useful
ideas from OSWM's historical Streamlit experiment but are not a claim that a
route is guaranteed accessible. Their values require participatory calibration
with users and accessibility specialists.

## Files

| File | Responsibility |
|---|---|
| `profile_rules.py` | Human-editable profile dictionaries |
| `profile_validation.py` | Structural and numerical safety checks |
| `grading.py` | Attribute normalization and grade calculation |
| `elevation.py` | Elevation-provider hierarchy and slope cache |
| `binary_graph.py` | Versioned typed-array graph serializer and spatial index |
| `routing_worker.js` | Indexed snapping, A* routing and bounded isochrone search off the browser main thread |
| `routing_demo.html` | Static MapLibre client with PMTiles network rendering and reachability controls |
| `../generation/routing_demo_gen.py` | Offline routing-data generation |
| `../generation/routing_tiles_gen.py` | Lightweight display PMTiles generation |

Policy changes should normally touch only `profile_rules.py`. The remaining
modules should not contain profile-specific accessibility judgments.

Every profile declares a `routing_mode`. The `distance` mode minimizes segment
length directly. The `accessibility_grade` mode consumes directional,
precomputed edge grades. Exactly one distance profile is required so every
accessibility route has an unambiguous comparison baseline.

## Grade terminology

- **Grade:** accessibility from 0 (unusable) to 100 (excellent).
- **Factor weight:** relative importance of an input such as width or slope.
- **Cost multiplier:** conversion of a grade into generalized routing
  resistance.
- **Event penalty:** fixed resistance for an event such as crossing a road.
- **Confidence:** completeness/reliability of the evidence, kept separate from
  accessibility.

Negative route costs are never allowed.

## Composition

Accessibility-profile factors are composed with a weighted harmonic mean:

```text
grade = sum(weights) / sum(weight / factor_grade)
```

This prevents one excellent characteristic from completely hiding a very poor
one. Hard barriers are evaluated first, while grade caps handle serious but not
universally impassable conditions.

The generator calculates separate forward and backward grades. Terrain rising
in feature-coordinate order is an ascent forward and a descent backward.
The distance profile needs no grades, so no redundant `distance_grade_*`
properties are written to every edge.

The same offline pass serializes the rounded topology and every profile's
directional edge costs into `network.oswmg`. The browser reads its arrays
directly, snaps clicks through the embedded uniform-grid segment index, and
runs A* in a Web Worker. Network drawing is intentionally separate: MapLibre
streams the much smaller `network.pmtiles` archive and never downloads the
analytical GeoParquet to calculate a route.

Displayed travel time is **accessibility-adjusted** for accessibility profiles.
The accumulated generalized resistance (length multiplied by the profile's
grade multiplier, plus event penalties) is divided by the profile speed. A
poor surface or difficult crossing therefore consumes more of the time budget
than the same physical distance under good conditions. These provisional
values describe comparative reachability; they are not measured journey times.

## Route comparison

When an accessibility profile is selected, the browser offers **Compare with
distance-only**. It calculates a second shortest-distance route between the
same snapped points, draws it as an offset orange dashed line, and reports its
distance plus the selected route's absolute and percentage difference. The
option is hidden when distance-only is already selected.

## Accessibility-adjusted isochrones

The routing page also has a **Reachability** mode. One origin click runs a
bounded Dijkstra search over the same directional typed-array graph and creates
cumulative polygons for the selected profile. Users choose the starting time,
increment in minutes and number of increments **after** the starting band.
The defaults (5, 5, 2) produce 5, 10 and 15-minute polygons; zero increments
produces only the starting band. Inputs use whole minutes, with at most 12
bands and a final cutoff no greater than 120 minutes. Changing a setting
recalculates the current origin and updates the legend and exported cutoffs.
Impassable
edges remain unreachable and poor conditions consume the budget according to
the profile's existing generalized costs.

Polygon boundaries are approximate. The worker rasterizes the reachable
portion of each network segment on a local metric grid, applies a small access
buffer and traces the resulting cells into Polygon or MultiPolygon geometries.
Using a shared grid guarantees that successive bands remain nested, preserves
disconnected components and holes, and avoids adding a server or a large
client-side geometry dependency.

The user can download the cumulative polygons as a GeoJSON FeatureCollection.
The export records the origin, outbound direction, cutoff, profile and speed,
ruleset identifiers, graph checksum, polygonization settings, generation time
and provisional-data disclaimer. This small, ephemeral client result does not
restore GeoJSON as a generated routing-network artifact.

## Slope source hierarchy

1. Numeric OSM `incline=*`.
2. A node-configured high-resolution DTM/COG.
3. A node-configured regional elevation model.
4. Copernicus DEM GLO-30 Public from the AWS Open Data Registry.
5. Copernicus DEM GLO-90 from AWS where a public 30 m tile is unavailable.
6. Unknown slope.

`incline:across=*` is independent and is never inferred from a terrain model.
Copernicus GLO-30 and GLO-90 are digital surface models: their results are
explicitly treated as low-confidence terrain trends, not measured sidewalk
slopes. Together they provide a globally valid default for OSWM nodes.

Nodes can override the provider list through `ELEVATION_CONFIG` in `config.py`.
The current template contains an example local COG entry.

Downloaded raster tiles are kept under ignored `.cache/`. Compact derived
slopes are stored in `data/routing/slope_cache.json`, keyed by geometry,
mapped incline and provider configuration. Unchanged edges therefore do not
need to be sampled again.

## Generated node files

| File | Contents |
|---|---|
| `data/routing/network.parquet` | Analytical geometry plus compact directional grades |
| `data/routing/network.oswmg` | Typed topology, profile costs and snapping index |
| `data/routing/network.pmtiles` | Lightweight MapLibre display network |
| `data/routing/profiles.json` | Browser-safe labels and graph contract |
| `data/routing/metadata.json` | Ruleset, graph checksum, provenance and grade audit |
| `data/routing/slope_cache.json` | Reusable derived slopes |
| `data/routing/tile_generation_report.json` | PMTiles generation validation |

`network.parquet` is the expert-facing scrutiny dataset and the direct source
for PMTiles generation. GeoJSON is not generated anywhere in the routing
pipeline; an isochrone GeoJSON exists only when a user calculates and exports
that derived result in the browser.

## Safely changing a profile

1. Edit only the relevant values in `profile_rules.py`.
2. Increment `PROFILE_RULESET_VERSION`.
3. Run:

   ```bash
   python -m unittest discover -s tests -p "test_routing_*.py" -v
   node --test tests/routing_worker.test.mjs
   ```

4. Generate at least one node and inspect `data/routing/metadata.json`.
5. Compare grade distributions and sample routes before propagating the
   codebase update to all nodes.

The generator records both a semantic version and a deterministic hash, making
it clear which rules produced each node artifact.

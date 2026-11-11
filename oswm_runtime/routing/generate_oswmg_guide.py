"""Generate the public binary-format guide and recorded benchmark tables."""

from __future__ import annotations

import json
import struct
import tempfile
from pathlib import Path

from .binary_graph import (
    MAGIC, SCHEMA_VERSION, HEADER_BYTES, TOPOLOGY_TOLERANCE,
    _COUNT_OFFSETS, _ARRAY_OFFSETS, build_binary_graph, read_graph_header,
)
from .generate_profile_guide import GUIDE_CSS, esc, table
from .profile_rules import ROUTING_PROFILES
from .profile_validation import public_profile_metadata


OUTPUT_PATH = Path(__file__).with_name("oswmg_guide.html")
BENCHMARK_PATH = Path(__file__).with_name("benchmark_results.json")
ARRAY_SPEC = {
    "longitudes": ("Float64", "V", "Longitude for each node, in degrees"),
    "latitudes": ("Float64", "V", "Latitude for each node, in degrees"),
    "adjacency_offsets": ("Uint32", "V + 1", "Start/end positions of each node’s outgoing edges"),
    "targets": ("Uint32", "E", "Target node ID for each directed edge"),
    "weights": ("Float32", "P × E", "Directional cost, grouped by profile"),
    "segment_a": ("Uint32", "S", "First node of each undirected snapping segment"),
    "segment_b": ("Uint32", "S", "Second node of each undirected snapping segment"),
    "cell_offsets": ("Uint32", "C + 1", "Start/end positions of each grid cell’s segment list"),
    "cell_segments": ("Uint32", "M", "Segment IDs belonging to each grid cell"),
}


def worked_example() -> dict:
    """Decode a real writer-produced fixture, so offsets and costs stay exact."""
    class Line:
        geom_type = "LineString"

        def __init__(self, coordinates):
            self.coords = coordinates

    metadata = public_profile_metadata(ROUTING_PROFILES)
    profiles = {key: metadata[key] for key in ("distance", "wheelchair")}
    rows = [
        {"geometry": Line([(0, 0), (.001, 0)]), "edge_kind": "sidewalk",
         "length_m": 111.2, "wheelchair_grade_fwd": 90, "wheelchair_grade_bwd": 75},
        {"geometry": Line([(.001, 0), (.002, 0)]), "edge_kind": "sidewalk",
         "length_m": 111.2, "wheelchair_grade_fwd": 45,
         "wheelchair_grade_bwd": 45, "wheelchair_allow_bwd": False},
    ]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "example.oswmg"
        audit = build_binary_graph(rows, {"profiles": profiles, "distance_profile_id": "distance"}, path)
        header = read_graph_header(path)
        data = path.read_bytes()
    arrays = {
        key: list(struct.unpack_from(fmt, data, header[f"{key}_offset"]))
        for key, fmt in (("adjacency_offsets", "<4I"), ("targets", "<4I"), ("weights", "<8f"))
    }
    return {"header": header, "audit": audit, "arrays": arrays}


def benchmark_section() -> str:
    if not BENCHMARK_PATH.exists():
        return '<section id="benchmark"><h2>Reproducible benchmark</h2><p>No recorded run is bundled yet. Run the benchmark instructions in the source repository.</p></section>'
    report = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    fmt = lambda value: "—" if value is None else f"{value:.3f}"
    env = report["environment"]
    result = '<section id="benchmark"><p class="eyebrow">Measured results</p><h2>Benchmark against client-side libraries</h2>'
    result += f'<p><strong>{esc(report["dataset"])}</strong>. {report["counts"]["nodes"]:,} nodes and {report["counts"]["directed_edges"]:,} directed edges. Recorded {esc(report["generated_at"])}.</p>'
    result += f'<p>{esc(env["runtime"])} / V8 {esc(env["v8"])} on {esc(env["cpu"])} ({esc(env["platform"])}, {esc(env["arch"])}). These are <strong>Node/V8 CPU measurements</strong> of the client-side code. Browser rendering, worker messaging, HTTP latency and library downloads are excluded.</p>'
    result += '<h3>Payload and startup</h3>'
    payload = report["payload_bytes"]
    result += table(["Representation", "Raw MiB", "gzip MiB", "Brotli MiB"], [
        [label, *(f'{payload[key + suffix] / 1048576:.2f}' for suffix in ("", "_gzip", "_brotli"))]
        for key, label in (("oswmg", ".oswmg"), ("geojson", "Equivalent segment GeoJSON"))
    ])
    result += '<p>Both contain identical precomputed profile costs; GeoJSON is derived from the same canonical graph. Compression uses gzip level 6 and Brotli quality 5. This isolates representation and search costs, rather than comparing different accessibility policies.</p>'
    result += table(["Engine", "Parse / initialize ms", "Shared graph or index setup ms", "First profile setup ms"], [
        [engine["label"], fmt(engine["input_parse_ms"]), fmt(engine["shared_setup_ms"]), fmt(engine["profiles"][0]["profile_setup_ms"])] for engine in report["engines"]
    ])
    result += '<p>Startup columns are single observations, separate from repeated query timings. File reads and module imports are excluded. OSWM initialization includes reading the header, creating typed-array views and preparing the worker’s profile lookup and snapping marks. GeoJSON Path Finder builds its topology separately for each profile; ngraph shares its graph across profile-specific search objects.</p>'
    result += '<h3>Route search by profile</h3>'
    route_rows, snap_rows = [], []
    for engine in report["engines"]:
        for profile in engine["profiles"]:
            for key, rows in (("routing", route_rows), ("snapping", snap_rows)):
                timing = profile[key]
                if timing["n"]:
                    rows.append([engine["label"], profile["profile_id"], timing["n"],
                                 fmt(timing["median_ms"]), fmt(timing["p95_ms"]),
                                 profile.get(f"{key}_mismatches", 0)])
    result += table(["Engine", "Profile", "Samples", "Median ms", "p95 ms", "Mismatches vs OSWM"], route_rows)
    result += '<h3>Nearest usable segment</h3>'
    result += table(["Engine", "Profile", "Samples", "Median ms", "p95 ms", "Mismatches vs OSWM"], snap_rows)
    result += '<h3>Isochrone diagnostic (OSWM only)</h3>'
    result += table(["Profile", "Origins", "Median ms", "p95 ms", "Bands returned per origin"], [
        [row["profile_id"], row.get("isochrone", {}).get("n", 0),
         fmt(row.get("isochrone", {}).get("median_ms")), fmt(row.get("isochrone", {}).get("p95_ms")),
         ", ".join(map(str, row.get("isochrone_band_counts", [])))]
        for row in report["engines"][0]["profiles"]
    ])
    result += '<p>These are three complete search-plus-polygonization requests per profile, each with 5-, 10- and 15-minute cutoffs and no warm-up. They are diagnostic observations, not a comparison against a different isochrone implementation.</p>'
    method = report["methodology"]
    result += f'<p>Seed {method["seed"]}; {method["route_pairs"]} vertex pairs and {method["snap_points"]} click positions per profile, repeated {method["repeats"]} times after {method["route_warmups"]} route and {method["snap_warmups"]} snapping warm-ups. Each engine runs in a fresh process. p95 is a sample percentile, not a browser responsiveness guarantee.</p>'
    result += '<p>Route endpoints are existing vertices in the largest distance-profile component. The four profiles receive the same pairs, including pairs that accessibility rules may disconnect. Costs and directional exclusions are identical; cost agreement allows 0.05 equivalent metres or 0.001% relative error. Snapping uses the same 100 m radius and outward eligibility, allowing 0.1 m distance disagreement because Turf uses great-circle geometry and OSWM uses a local planar projection.</p>'
    result += '<p><strong>Scope matters.</strong> Turf’s nearest-point operation is measured both as a full scan and with an RBush spatial index. Turf’s shortestPath solves obstacle avoidance on a grid, rather than this preweighted pedestrian graph, so it receives no network-routing score. GeoJSON Path Finder and ngraph.path are the network-routing comparators. Search timings use common vertex endpoints; full click-to-route UI latency and arbitrary partial-edge attachment are not measured. OSWM also constructs its route geometry and distance; ngraph’s timed operation returns node IDs.</p>'
    result += '<p class="note"><strong>Correctness finding:</strong> GeoJSON Path Finder 2.1.0 can discard a cheaper parallel corridor during graph compaction. The benchmark includes a small regression fixture where it returns cost 800 while OSWM and ngraph preserve a cost-300 path. The mismatch columns report affected Milan queries; its timings therefore do not establish a speed comparison between equally correct solutions. ngraph provides the independent routing-cost cross-check.</p>'
    result += '<p>The figures may favour different engines on different tasks. They are one controlled dataset/run, not a universal ranking. Approximate process memory deltas and route outcomes are available in the raw report; they exclude the common validation graph and are not browser peak-RAM measurements.</p>'
    result += table(["Library", "Pinned version"], [[key, value] for key, value in report["versions"].items()])
    result += f'<p>Input graph SHA-256: <code>{esc(report["graph_sha256"])}</code>. Routing rules {esc(report["ruleset_version"])} / <code>{esc(report["ruleset_hash"])}</code>.</p>'
    return result + '<p><a href="benchmark_results.json">Download the recorded results</a> · <a href="https://github.com/kauevestena/oswm_codebase/tree/main/benchmarks">Reproduction scripts and methodology</a></p></section>'


def generate() -> str:
    example = worked_example()
    header, audit, arrays = example["header"], example["audit"], example["arrays"]
    header_rows = [[0, 8, "ASCII", "magic", MAGIC.decode()], [8, 4, "Uint32", "schema_version", SCHEMA_VERSION],
                   [12, 4, "Uint32", "header_bytes", HEADER_BYTES]]
    header_rows += [[offset, 4, "Uint32", name, header[name]] for name, offset in _COUNT_OFFSETS.items()]
    header_rows.append([44, 4, "Reserved", "unused", "zero"])
    header_rows += [[offset, 8, "Uint64", name + " byte offset", header[name + "_offset"]] for name, offset in _ARRAY_OFFSETS.items()]
    header_rows += [[120, 16, "Reserved", "unused", "zero"],
                    [136, 32, "4 × Float64", "min lon, min lat, max lon, max lat", "0, 0, 0.002, 0"],
                    [168, 8, "Float64", "topology tolerance (degrees)", TOPOLOGY_TOLERANCE],
                    [176, 16, "Reserved", "unused", "zero"]]
    schema_table = table(["Byte offset", "Bytes", "Type", "Field", "Example value"], header_rows)
    payload_table = table(["Array", "Type", "Elements", "Purpose", "Example byte offset"], [
        [name, *ARRAY_SPEC[name], header[name + "_offset"]] for name in _ARRAY_OFFSETS
    ])
    edge_rows = []
    for source in range(header["node_count"]):
        for e in range(arrays["adjacency_offsets"][source], arrays["adjacency_offsets"][source + 1]):
            wheelchair = arrays["weights"][header["directed_edge_count"] + e]
            edge_rows.append([e, source, arrays["targets"][e], f'{arrays["weights"][e]:.3f}',
                              "Infinity (blocked)" if wheelchair == float("inf") else f"{wheelchair:.3f}"])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>OSWM · Inside the .oswmg routing format</title><style>{GUIDE_CSS}</style></head>
<body><header><a href="profile_guide.html">Profiles and isochrones</a> · <a href="routing_demo.html">Routing demo</a>
<h1>Inside .oswmg.<br>A graph ready for the browser.</h1>
<p>How OSWM creates its binary routing format, how its bytes are arranged, and where the speed comes from.</p>
<p>Current schema {SCHEMA_VERSION} · {HEADER_BYTES}-byte header · magic <code>{MAGIC.decode()}</code></p></header>
<main><nav aria-label="Guide contents"><a href="#creation">Creation</a><a href="#layout">Binary layout</a><a href="#example">Worked example</a><a href="#execution">Browser execution</a><a href="#performance">Performance design</a><a href="#benchmark">Benchmark</a><a href="#limits">Tradeoffs</a></nav>
<section id="creation"><h2>Why OSWM created this format</h2>
<p>The routing demo needs connectivity and costs, whereas the map needs drawable geometry. OSWM’s custom <code>.oswmg</code> file is a prebuilt binary graph for the first task. Python prepares the topology, profile costs and spatial index once during node generation. A static web server can then deliver that graph directly to a JavaScript worker, alongside separate PMTiles for drawing the network.</p>
<h3>From processed data to bytes</h3><ol>
<li><strong>Prepare evidence.</strong> The generation pipeline reads processed sidewalks, crossings and other footways, associates nearby crossing/kerb evidence, resolves slope and calculates separate forward and backward accessibility grades.</li>
<li><strong>Assign node IDs.</strong> Existing geometry vertices are merged by rounded coordinate keys using a tolerance of {TOPOLOGY_TOLERANCE:g} degrees. This is an angular tolerance: approximately 1.1 m north–south, with longitude distance depending on latitude. The last raw coordinate seen for a key is retained as its representative. IDs are dense local array positions, not OSM IDs.</li>
<li><strong>Create directed edges.</strong> Each consecutive pair of distinct vertex IDs becomes two directed entries. Their profile costs can differ; an excluded direction has positive Infinity as its weight. A distance edge uses its haversine length. Accessibility edges use length × multiplier plus the feature event penalty’s proportional share.</li>
<li><strong>Arrange outgoing edges.</strong> Entries are sorted by source ID, then target ID. The writer stores adjacency offsets, targets and one block of costs per profile. Duplicate source–target entries use the last feature encountered, preserving the existing topology reducer’s behaviour.</li>
<li><strong>Index segments.</strong> Unique undirected node pairs form a snapping segment list. A bounded uniform grid stores references to every segment whose bounding box overlaps a cell. This is a conservative candidate index, not a second routing network.</li>
<li><strong>Serialize and audit.</strong> The writer computes absolute byte offsets, writes a fixed header followed by contiguous arrays, atomically replaces the file and records SHA-256 and counts in the generated metadata. Profile IDs and their ordering are kept in <code>profiles.json</code>.</li></ol>
<p>Lines that merely cross geometrically are not automatically connected; this builder uses existing rounded vertices. The binary graph inherits the processed network’s connectivity.</p></section>
<section id="layout"><h2>Internal structure, byte by byte</h2>
<p>All multibyte numbers use <strong>little-endian</strong> order. The header starts at byte zero, followed immediately by the arrays below. Header array pointers are absolute byte offsets from the start of the file; adjacency and cell offsets are array indices, not byte addresses.</p>
<details><summary>Complete {HEADER_BYTES}-byte header</summary>{schema_table}</details>
<p>Symbols: <strong>V</strong> nodes; <strong>E</strong> directed edges; <strong>P</strong> profiles; <strong>S</strong> undirected segments; <strong>C</strong> grid columns × rows; <strong>M</strong> total cell memberships. A segment can belong to several cells, so M can exceed S.</p>
{payload_table}
<p><code>Float64</code> takes 8 bytes, <code>Float32</code> and <code>Uint32</code> take 4 bytes. The arrays contain no repeated feature/property objects or coordinate strings. Positive IEEE-754 Infinity is a blocked weight. Profile names, labels, speeds, rules and original source attributes are not embedded in these arrays.</p>
<p class="formula">Total bytes = {HEADER_BYTES} + 16V + 4(V + 1) + 4E + 4PE + 8S + 4(C + 1) + 4M</p>
<p>The current layout places the Float64 arrays first at aligned offsets. The browser uses <code>DataView</code> for header fields and native typed-array views into the fetched <code>ArrayBuffer</code> on little-endian machines. That avoids copying each payload array into JavaScript objects; downloading the buffer and allocating search state still use memory.</p></section>
<section id="example"><h2>A worked three-node example</h2>
<p>Consider A (node 0) at [0, 0], B (node 1) at [0.001, 0], and C (node 2) at [0.002, 0]. There are two sidewalk segments. The example assigns explicit directional grades to demonstrate encoding; these are illustrative inputs, not a field assessment. The values and byte offsets on this page are decoded from a file generated by the actual Python writer.</p>
<pre><code>profile order:      [distance, wheelchair]
adjacency_offsets:  {esc(arrays["adjacency_offsets"])}
targets:            {esc(arrays["targets"])}</code></pre>
<p>Node B’s outgoing entries occupy positions 1 through 2: start at <code>adjacency_offsets[1] = 1</code>, stop before <code>adjacency_offsets[2] = 3</code>. Their targets are A and C. This arrangement is called <strong>compressed sparse row (CSR)</strong>; the source node is implicit in the offset range.</p>
{table(["Directed edge index", "Source", "Target", "Distance cost (m)", "Wheelchair cost (equivalent m)"], edge_rows)}
<p>For profile index p and directed edge index e, read <code>weights[p × E + e]</code>. Here A→B is edge 0 and B→A is edge 1. The wheelchair profile can travel B→C, while C→B is blocked. Each profile shares the same topology and uses its own cost block. This complete example occupies <strong>{audit["byte_size"]} bytes</strong>.</p></section>
<section id="execution"><h2>How the browser uses it</h2>
<h3>Load once per worker</h3><p>The client reads <code>profiles.json</code> and gives its graph URL and profile order to a Web Worker. The URL is versioned with the recorded graph checksum for cache invalidation. The worker checks magic, schema, header size, array offsets/truncation and profile count, then creates typed-array views. These are compatibility checks, not a full cryptographic verification of the downloaded graph.</p>
<h3>Snap a click</h3><p>The worker starts in the click’s grid cell and expands through neighbouring cells. It projects onto candidate segments, filters out unusable profile positions, and stops when unvisited cells cannot offer a nearer point or are beyond the 100 m access radius. Per-search marks avoid testing a segment repeatedly when it appears in several cells. The result records a segment ID and fraction along it, rather than requiring the click to coincide with an existing node.</p>
<h3>Find a route</h3><p>A* searches outgoing adjacency ranges using a min-heap. The heuristic is a conservative straight-line distance scaled for the profile, with a small margin for Float32 rounding; an unavailable heuristic falls back to zero. Nonfinite weights are skipped. Endpoint partial-edge costs connect snapped positions to their adjacent nodes, and the resulting predecessor chain reconstructs route coordinates. Distances and predecessors are temporary per-search arrays.</p>
<h3>Calculate isochrones</h3><p>A bounded Dijkstra search explores outward while accumulated profile cost is within the largest time budget. It finds reachable nodes and partial segments for each cutoff. Those segments are buffered/rasterized on a shared local grid and converted to cumulative polygons. Network search and polygon construction are separate work; large budgets or many bands can make polygonization expensive.</p></section>
<section id="performance"><h2>Where the speed comes from</h2>
{table(["Design choice", "Work it saves or moves"], [
    ["Offline graph construction", "Topology, directional costs and spatial indexing are prepared during publication instead of on each browser load."],
    ["Binary numbers and dense IDs", "The browser avoids parsing coordinate strings and rebuilding a graph from feature/property objects."],
    ["Contiguous typed arrays", "Outgoing edges and profile costs are addressed by array position; profile changes reuse the topology."],
    ["Uniform-grid snapping index", "Nearby candidate segments are examined instead of scanning every feature for every click."],
    ["A* plus min-heap", "A geographic lower bound can reduce exploration compared with an uninformed full-graph search."],
    ["Web Worker", "Search work runs off the UI thread, allowing map interaction to remain responsive; threading does not itself reduce CPU work."],
    ["Separate PMTiles display", "Map drawing can stream tiles independently of the analytical graph; the router does not fetch GeoParquet to calculate a path."],
])}
<p>Compact storage is not compression: the current .oswmg payload is uncompressed binary and can also benefit from HTTP compression. “Fast” describes these design choices, not a fixed latency guarantee. A competing graph library can still win a particular query; the recorded benchmark below measures this explicitly.</p></section>
{benchmark_section()}
<section id="limits"><h2>Tradeoffs and compatibility</h2>
<p>The full graph is fetched for a node, so initial transfer and RAM still grow with network size and number of profiles. Costs use Float32 precision, while coordinates use Float64. The snapping grid adds some duplicated segment references to accelerate searches. Disconnected components can force more search work, and A* has no universal bound on the fraction of the graph it must visit.</p>
<p>This is an OSWM-specific runtime format, not a replacement for the node’s analytical GeoParquet or a general geospatial exchange standard. The companion profile order must match the graph. The current worker accepts schema {SCHEMA_VERSION}; a layout change needs a coordinated writer/reader version update. Native payload views assume a little-endian browser platform.</p>
<p>Source of truth: <a href="https://github.com/kauevestena/oswm_codebase/blob/main/routing/binary_graph.py">Python writer</a>, <a href="https://github.com/kauevestena/oswm_codebase/blob/main/routing/routing_worker.js">browser worker</a> and <a href="https://github.com/kauevestena/oswm_codebase/blob/main/generation/routing_demo_gen.py">data generation pipeline</a>. Benchmark comparator documentation: <a href="https://turfjs.org/docs/api/nearestPointOnLine">Turf nearestPointOnLine</a>, <a href="https://turfjs.org/docs/api/shortestPath">Turf shortestPath</a>, <a href="https://github.com/perliedman/geojson-path-finder">GeoJSON Path Finder</a>, <a href="https://github.com/anvaka/ngraph.path">ngraph.path</a>, <a href="https://github.com/mourner/rbush">RBush</a>.</p></section>
<footer><a class="guide-button" href="profile_guide.html">← Return to profile explanations</a> · <a href="routing_demo.html">Open routing demo</a></footer></main></body></html>
'''


if __name__ == "__main__":
    OUTPUT_PATH.write_text(generate(), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")

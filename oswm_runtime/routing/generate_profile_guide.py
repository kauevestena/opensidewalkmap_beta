"""Render the public routing guide directly from the live profile policy.

Run ``python -m routing.generate_profile_guide`` after a policy edit. A freshness
test checks the committed page; the node runtime publisher copies it alongside
the demo and worker.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from .profile_rules import PROFILE_RULESET_VERSION, ROUTING_PROFILES
from .profile_validation import profile_ruleset_hash, validate_profiles


OUTPUT_PATH = Path(__file__).with_name("profile_guide.html")

# Both public guides share a visual language without external dependencies.
GUIDE_CSS = """
:root { color-scheme: light; --ink:#172d36; --muted:#4e626a; --line:#d7e2e4; --accent:#087b70; }
* { box-sizing:border-box; } body { margin:0; color:var(--ink); background:#f4f7f7; font:17px/1.65 system-ui,sans-serif; }
header { background:#123e45; color:white; padding:3rem max(1.2rem,calc((100vw - 1060px)/2)); }
header a { color:#c4f6e5; } header h1 { font-size:clamp(2rem,5vw,3.2rem); line-height:1.15; max-width:850px; margin:1rem 0; }
main { max-width:1100px; margin:auto; padding:1.4rem; } section { scroll-margin-top:1rem; background:white; border:1px solid var(--line); border-radius:12px; padding:clamp(1rem,3vw,2rem); margin:1.5rem 0; }
nav { display:flex; flex-wrap:wrap; gap:.65rem 1.1rem; margin:1rem 0; } a { color:#006b63; text-underline-offset:.18em; } a:focus-visible,summary:focus-visible { outline:3px solid #b76204; outline-offset:4px; }
a.guide-button { display:inline-block; padding:.8rem 1.1rem; background:#087b70; color:white; border-radius:8px; text-decoration:none; font-weight:650; }
h2 { line-height:1.25; font-size:1.75rem; margin:.25rem 0 1rem; } h3 { margin:1.7rem 0 .6rem; } h4 { margin:1rem 0 .4rem; }
.eyebrow { text-transform:uppercase; letter-spacing:.09em; font-size:.8rem; font-weight:750; color:var(--muted); }
.note { border-left:4px solid var(--accent); padding:.8rem 1rem; background:#e9f5f1; }
.table-scroll { overflow-x:auto; margin:.8rem 0 1rem; } table { border-collapse:collapse; width:100%; font-size:.94rem; } th,td { text-align:left; padding:.65rem .8rem; border:1px solid var(--line); vertical-align:top; } th { background:#eaf2f1; }
code { overflow-wrap:anywhere; font-size:.92em; } pre { padding:1rem; background:#eef4f5; border-radius:7px; overflow-x:auto; font-size:.88rem; } details { border:1px solid var(--line); border-radius:7px; padding:.7rem 1rem; margin:.7rem 0; } summary { cursor:pointer; color:#075e56; font-weight:650; }
.formula { padding:1rem; background:#eef4f5; border-radius:7px; overflow-wrap:anywhere; } footer { padding:1rem 0 3rem; color:var(--muted); }
@media(max-width:520px) { body { font-size:16px; } main { padding:.6rem; } th,td { padding:.45rem; } }
"""

PROFILE_NOTES = {
    "distance": (
        "The standard walking baseline chooses the shortest geometric path in the "
        "available pedestrian network. It does not apply accessibility grades, "
        "steps exclusions, access-tag barriers or crossing penalties. A short "
        "route is therefore not evidence that it is usable by a particular person."
    ),
    "wheelchair": (
        "Smoothness, width, longitudinal slope and crossing kerbs carry high weights. "
        "Steps, wheelchair=no, impassable surfaces and restricted pedestrian access "
        "are excluded. Width at or below 0.60 m and a raised crossing kerb also "
        "produce a zero factor grade. Unknown width, surface and slopes receive "
        "conservative provisional scores; they are not assumed ideal."
    ),
    "blind": (
        "Tactile paving and crossing type carry the highest weights; kerb detectability "
        "also matters. A flush kerb alone is less detectable than a raised one. "
        "Explicitly absent tactile paving receives a very poor score, rather than "
        "excluding every such crossing. Steps remain usable with a grade cap and "
        "an event penalty. This profile does not model audible signals, guide-dog "
        "needs or every obstacle a cane user may encounter."
    ),
    "elderly": (
        "Smoothness, longitudinal slope and crossing type carry the highest weights, "
        "followed by surface material and crossing kerbs. Raised kerbs and steps "
        "receive severe grade caps; stairs also have a substantial event penalty. "
        "Narrow paths remain costly rather than universally excluded. This is a "
        "provisional reduced-mobility model, not a description of every older person."
    ),
}


def esc(value: object) -> str:
    return html.escape(str(value))


def number(value: float) -> str:
    return f"{value:g}"


def table(headers: list[str], rows: list[list[object]]) -> str:
    return (
        '<div class="table-scroll"><table><thead><tr>'
        + "".join(f'<th scope="col">{esc(item)}</th>' for item in headers)
        + "</tr></thead><tbody>"
        + "".join("<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>" for row in rows)
        + "</tbody></table></div>"
    )


def band_rows(bands: list[dict]) -> list[list[object]]:
    rows = []
    previous = None
    for band in bands:
        maximum = band["max"]
        if maximum is None:
            interval = f"> {number(previous)}" if previous is not None else "All values"
        elif previous is None:
            interval = f"≤ {number(maximum)}"
        else:
            interval = f"> {number(previous)} and ≤ {number(maximum)}"
        rows.append([interval, band["grade"]])
        previous = maximum
    return rows


def condition(rule: dict) -> str:
    operators = {
        "equals": "equals", "in": "is one of", "contains": "contains",
        "lt": "<", "lte": "≤", "gt": ">", "gte": "≥",
    }
    value = rule["value"]
    if isinstance(value, list):
        value = ", ".join(map(str, value))
    return f"{rule['field']} {operators[rule['operator']]} {value}"


def scope(rule: dict) -> str:
    return ", ".join(rule.get("applies_to", [])) or "All edge types"


def factor_details(factor_id: str, rule: dict) -> str:
    label = factor_id.replace("_", " ").capitalize()
    text = f'<details><summary>{esc(label)}: full scoring table</summary>'
    text += f'<p>Input: <code>{esc(rule["field"])}</code>. '
    text += f'Unknown or unmodelled value: {rule["unknown_grade"]}/100.</p>'
    if rule["type"] == "categorical":
        text += table(["Mapped value", "Factor grade"], [[key, value] for key, value in rule["values"].items()])
        text += f'<p>When multiple values are associated with an edge, use their {esc(rule.get("aggregation", "minimum"))} score.</p>'
    elif rule["type"] == "numeric_bands":
        text += table(["Value (m for width; % for slope)", "Factor grade"], band_rows(rule["bands"]))
        if rule.get("absolute"):
            text += "<p>The absolute value is used.</p>"
    else:
        for direction in ("ascending", "descending"):
            text += f'<h4>{direction.capitalize()} slope (%)</h4>'
            text += table(["Absolute slope", "Factor grade"], band_rows(rule[direction]))
        if "zero_grade_min_confidence" in rule:
            text += (
                f'<p>A zero slope grade requires source confidence ≥ {rule["zero_grade_min_confidence"]}/100. '
                f'Below this threshold, use {rule["unconfirmed_zero_grade"]}/100 instead: '
                "a severe difficulty penalty, without declaring a confirmed barrier. "
                "This does not override other exclusions.</p>"
            )
    return text + "</details>"


def profile_section(profile_id: str, profile: dict) -> str:
    status = "Provisional accessibility model" if profile["provisional"] else "Distance baseline"
    result = (
        f'<section id="profile-{esc(profile_id)}"><p class="eyebrow">{status}</p>'
        f'<h2>{esc(profile["label"])}</h2><p>{esc(profile["description"])}</p>'
        f'<p>{esc(PROFILE_NOTES.get(profile_id, ""))}</p>'
        f'<p><strong>Reference speed: {number(profile["speed_kmh"])} km/h.</strong></p>'
    )
    if profile["routing_mode"] == "distance":
        return result + "<p>Routing cost equals physical segment length. Time equals distance divided by this speed.</p></section>"

    result += "<h3>What affects this profile</h3>"
    result += table(
        ["Factor", "Relative weight", "Unknown grade / 100", "Applies to"],
        [[key.replace("_", " "), rule["factor_weight"], rule["unknown_grade"], scope(rule)] for key, rule in profile["factors"].items()],
    )
    result += "<p>Higher weight means more influence. These are relative weights, not percentages.</p>"
    result += "".join(factor_details(key, rule) for key, rule in profile["factors"].items())
    result += "<h3>Hard exclusions</h3>"
    result += table(["Condition", "Applies to"], [[condition(rule), scope(rule)] for rule in profile.get("barriers", [])])
    result += "<p>Any applicable zero factor grade also excludes the edge. An unavailable event cost excludes that edge type.</p>"
    result += "<h3>Grade caps</h3><p>Caps only reduce a positive grade; they never reopen a blocked edge.</p>"
    result += table(["Condition", "Maximum grade", "Applies to"], [[condition(rule), rule["max_grade"], scope(rule)] for rule in profile.get("grade_caps", [])])
    result += "<h3>From grades to route costs</h3>"
    result += table(["Final rounded grade", "Length multiplier"], [
        [f'{band["min_grade"]}–{100 if index == 0 else profile["cost"]["grade_multipliers"][index - 1]["min_grade"] - 1}', f'{number(band["multiplier"])}×']
        for index, band in enumerate(profile["cost"]["grade_multipliers"])
    ])
    result += table(["Event / edge type", "Added equivalent metres per feature"], [
        [key, "Excluded" if value is None else number(value)]
        for key, value in profile["cost"]["event_penalties_m"].items()
    ])
    return result + "</section>"


def generate() -> str:
    """Return deterministic, standalone HTML suitable for runtime publication."""
    validate_profiles(ROUTING_PROFILES)
    rules_hash = profile_ruleset_hash(ROUTING_PROFILES)
    worker = Path(__file__).with_name("routing_worker.js").read_text(encoding="utf-8")
    cell_size = re.search(r"const ISOCHRONE_CELL_SIZE_M = (\d+);", worker).group(1)
    buffer_size = re.search(r"const ISOCHRONE_BUFFER_M = (\d+);", worker).group(1)
    links = "".join(f'<a href="#profile-{esc(key)}">{esc(value["label"])}</a>' for key, value in ROUTING_PROFILES.items())
    profiles = "".join(profile_section(key, value) for key, value in ROUTING_PROFILES.items())
    return f'''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>OSWM · Routing profiles and isochrones explained</title>
<style>{GUIDE_CSS}</style></head>
<body><header><a href="../../index.html">OSWM node</a> · <a href="routing_demo.html">Back to routing</a>
<h1>Why this route?<br>Profiles and isochrones explained.</h1>
<p>What each profile optimizes, what can block a route, and what a coloured reachability area actually means.</p>
<p>Policy version {PROFILE_RULESET_VERSION} · <code>{rules_hash}</code></p>
</header><main>
<nav aria-label="Guide contents"><a href="#how-it-works">How routes are chosen</a>{links}<a href="#isochrones">Isochrones</a><a href="#troubleshooting">Unexpected results</a><a href="#evidence">Data and confidence</a></nav>
<p class="note">Accessibility profiles are provisional and need calibration with users and accessibility specialists. A computed route is a model result, not a guarantee of accessibility. An absent route is not proof that travel is impossible.</p>
<p id="nodePolicyStatus" role="status">Guide tables describe the policy version above. The node’s generated graph may use an earlier version.</p>
<p><a class="guide-button" href="oswmg_guide.html">Inside .oswmg: how the fast router works →</a></p>
<section id="how-it-works"><h2>How the router chooses a route</h2>
<ol><li><strong>Place the endpoints.</strong> Each click is snapped to a usable segment for the selected profile, within 100 m. Changing profiles snaps the original clicks again. The displayed offset is not a verified access path and is not included in distance or time.</li>
<li><strong>Check exclusions.</strong> Explicit barriers and applicable zero factor grades remove an edge for that profile. Other poor conditions increase its cost.</li>
<li><strong>Combine the evidence.</strong> For accessibility profiles, the weighted harmonic mean combines the applicable factor grades; a very poor factor cannot be hidden by several excellent ones. Grade caps are applied, and the result is rounded to 0–100.</li>
<li><strong>Minimize total cost.</strong> The router selects the lowest-cost connected path. Forward and backward grades can differ because ascending and descending slopes have different effects.</li></ol>
<p class="formula">Combined grade = sum of factor weights ÷ sum of (weight ÷ factor grade)<br>
Accessibility cost = segment length × grade multiplier + share of event penalty</p>
<p>Any zero factor makes the combined grade zero, subject to the confidence rule in the slope tables. Event penalties are equivalent metres of resistance, not extra physical distance. They are distributed across the segments of each source feature, rather than charged at every geometry vertex.</p>
<p>The map reports <strong>physical route distance</strong>. The accessibility-adjusted time uses accumulated cost divided by the profile speed. These minutes express comparative difficulty, not measured journey durations. The distance profile uses physical distance and its own speed.</p>
<p>For example, a 100 m wheelchair crossing with final grade 60 has cost 100 × 1.6 + 15 = 175 equivalent metres. At 3.5 km/h this gives 3 adjusted minutes. The route is still 100 m long.</p>
<p><strong>Compare with distance-only</strong> draws an orange dashed shortest path between the same snapped endpoints, alongside the selected blue route. The reported difference compares physical lengths. Its time uses the baseline speed, so it is not the selected profile’s time on that alternative. The baseline does not certify accessibility.</p>
</section>{profiles}
<section id="isochrones"><p class="eyebrow">Reachability mode</p><h2>How to read the isochrones</h2>
<p>An isochrone is an approximate area around network segments reachable <strong>outward from one origin</strong> within a cost budget. Every profile uses its own speed and the same directional edge costs and exclusions as point-to-point routing.</p>
<p class="formula">Budget in equivalent metres = cutoff minutes × profile speed in km/h × 1000 ÷ 60</p>
<p>Distance-only bands use geometric distance at 5 km/h. Accessibility bands use adjusted minutes: difficult surfaces and crossings consume more of the budget, and excluded edges cannot be traversed. Smaller polygons do not necessarily mean a person actually walks that much slower. An inbound journey can have different reachability.</p>
<h3>Choose the bands</h3><p><strong>Starting time</strong> is the first cutoff. <strong>Increment</strong> is the number of minutes added between cutoffs. <strong>Number of increments</strong> counts additional bands after the first. The defaults 5, 5 and 2 produce 5-, 10- and 15-minute polygons. Zero increments produces one polygon. Use whole minutes: up to 12 bands, with the last cutoff no greater than 120 minutes.</p>
<p>Bands are cumulative and nested: a 10-minute polygon includes the 5-minute reach. Each colour matches its cutoff in the legend. Changing the profile or settings recalculates the current origin.</p>
<h3>What the filled area does and does not show</h3>
<p>A bounded network search finds reachable edges and partial edges, then rasterizes and buffers them on a shared local grid. The base grid is {cell_size} m, coarsened for large results; the access buffer is {buffer_size} m. Separate components and holes can remain.</p>
<p>The fill is a cartographic approximation around reachable paths. It does not establish access to every parcel, building or spot inside the polygon; a buffer can overlap a wall, river or inaccessible property. It does not add off-network shortcuts to the routing search. At a small budget the polygon may end partway along an edge.</p>
<h3>Download GeoJSON</h3><p>The export contains one cumulative Polygon or MultiPolygon per cutoff, coordinates in longitude/latitude (OGC:CRS84), and metadata recording the snapped origin, outward direction, profile, speed, cutoff, ruleset version/hash, graph checksum, generation time and polygonization settings. Preserve this metadata when comparing results; graphs and provisional policy can change.</p>
</section>
<section id="troubleshooting"><h2>Why a route can look unexpected</h2>
<ul><li><strong>Standard walking works, another profile fails.</strong> The baseline ignores accessibility exclusions. A profile can disconnect at steps, a restricted path, a very narrow section or a zero-grade crossing. The graph can also contain disconnected mapping islands.</li>
<li><strong>The endpoints move when changing profiles.</strong> A formerly selected segment may be excluded. The tool uses the nearest usable segment within 100 m and shows the offset; it does not search for an arbitrary distant connected component.</li>
<li><strong>The route is much longer.</strong> Lower resistance can outweigh extra distance. Use the distance-only comparison and inspect the factor and penalty tables.</li>
<li><strong>Times are large or reachability is small.</strong> Missing evidence receives the listed unknown grades. Several moderately poor factors and crossing penalties can substantially increase resistance.</li>
<li><strong>No route still appears after snapping succeeds.</strong> Locally usable endpoints may belong to different profile-connected components. The tool never silently substitutes a standard walking route as an accessible one.</li>
<li><strong>A barrier shown in hazard analysis is still traversed.</strong> Hazard categories and routing costs are separate policies. Hazard severity is not a routing multiplier; read the <a href="../hazard_analysis/classification_guide.html">hazard classification guide</a> alongside these tables.</li></ul>
</section>
<section id="evidence"><h2>Data, uncertainty and provenance</h2>
<p>Mapped OpenStreetMap tags supply surface, smoothness, width, access and crossing evidence. Crossing kerbs and tactile paving include nearby associated kerb information. Missing or unmodelled values receive the fallback grades shown above. Confidence records evidence completeness separately from accessibility grade; it is not a probability that a route is safe.</p>
<p>Longitudinal slope uses numeric mapped incline first, then a configured local DTM, a regional model, Copernicus GLO-30, GLO-90, or unknown slope. The global products are coarse digital surface models and describe terrain trends, not measured sidewalk slopes. A coarse estimate alone cannot confirm the zero-grade slope barrier: it keeps a severe low score instead. Higher-confidence or numeric mapped slopes can still exclude edges. Cross slope is based only on mapped <code>incline:across</code>, never inferred from terrain.</p>
<p>The network’s topology uses rounded existing geometry vertices; crossing lines do not automatically become connected at every geometric intersection. The demo does not model live works, temporary closures, traffic-signal waiting times or all personal requirements. Graph edges are available in both directions subject to profile grades; general OSM turn and one-way restrictions are not a complete navigation model here.</p>
<p>Inspect this node’s <a href="../../data/routing/metadata.json">generation audit</a>, <a href="../../data/routing/profiles.json">profile and graph metadata</a> and <a href="../../data/routing/network.parquet">analytical GeoParquet</a>. Policy tables on this page are generated from <code>routing/profile_rules.py</code>; the generic grading engine, not the hazard categories, produces routing grades.</p>
</section><footer><a href="routing_demo.html">Return to the routing demo</a> · <a href="../../index.html">Node home</a></footer>
</main><script>
fetch('../../data/routing/profiles.json', {{cache:'no-store'}}).then(response => {{
    if (!response.ok) throw new Error('Profile metadata unavailable');
    return response.json();
}}).then(data => {{
    const matches = data.ruleset_hash === '{rules_hash}';
    document.getElementById('nodePolicyStatus').textContent = matches
        ? `This node’s graph uses policy ${{data.ruleset_version}}, matching this guide.`
        : `This node’s graph uses policy ${{data.ruleset_version}} (${{data.ruleset_hash}}). This guide describes {PROFILE_RULESET_VERSION} ({rules_hash}); its tables will apply after routing data is regenerated.`;
}}).catch(() => {{
    document.getElementById('nodePolicyStatus').textContent = 'Node profile metadata is unavailable here. Check the graph policy version before comparing results with these tables.';
}});
</script></body></html>
'''


if __name__ == "__main__":
    OUTPUT_PATH.write_text(generate(), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")

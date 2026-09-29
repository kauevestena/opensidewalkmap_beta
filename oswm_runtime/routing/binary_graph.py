"""Serialize the routing network into a compact, browser-readable graph.

The format is deliberately simple: a fixed little-endian header followed by
typed arrays.  It contains one shared topology, one weight array per routing
profile, and a uniform-grid segment index used to snap map clicks without a
linear scan of every feature.

The browser implementation lives in :mod:`routing.routing_worker.js`.  Keep
``MAGIC``, ``SCHEMA_VERSION`` and the header layout in sync with that worker.
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import sys
import tempfile
from array import array
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any


MAGIC = b"OSWMGB02"
SCHEMA_VERSION = 2
HEADER_BYTES = 192
TOPOLOGY_TOLERANCE = 1e-5
EARTH_RADIUS_M = 6_371_008.8

_COUNT_OFFSETS = {
    "node_count": 16,
    "directed_edge_count": 20,
    "profile_count": 24,
    "segment_count": 28,
    "grid_cols": 32,
    "grid_rows": 36,
    "cell_membership_count": 40,
}
_ARRAY_OFFSETS = {
    "longitudes": 48,
    "latitudes": 56,
    "adjacency_offsets": 64,
    "targets": 72,
    "weights": 80,
    "segment_a": 88,
    "segment_b": 96,
    "cell_offsets": 104,
    "cell_segments": 112,
}


def _haversine_m(left: Sequence[float], right: Sequence[float]) -> float:
    lon1, lat1 = math.radians(float(left[0])), math.radians(float(left[1]))
    lon2, lat2 = math.radians(float(right[0])), math.radians(float(right[1]))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    value = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(value)))


def _line_coordinates(geometry: Any) -> Iterable[Sequence[Any]]:
    """Yield coordinate sequences from Shapely routing geometries."""

    geometry_type = getattr(geometry, "geom_type", None)
    if geometry_type == "LineString":
        yield geometry.coords
    elif geometry_type == "MultiLineString":
        for part in geometry.geoms:
            yield part.coords


def _profile_order(profile_payload: Mapping[str, Any]) -> list[str]:
    profiles = profile_payload.get("profiles")
    if not isinstance(profiles, Mapping) or not profiles:
        raise ValueError("profile payload must contain routing profiles")
    distance_id = profile_payload.get("distance_profile_id")
    if distance_id not in profiles:
        raise ValueError("profile payload has no valid distance_profile_id")
    return [distance_id, *(key for key in profiles if key != distance_id)]


def _grade_multiplier(profile: Mapping[str, Any], grade: float) -> float | None:
    cost = profile.get("cost") or {}
    for band in cost.get("grade_multipliers") or []:
        if grade >= float(band["min_grade"]):
            return float(band["multiplier"])
    return None


def _directional_weight(
    profile_id: str,
    profile: Mapping[str, Any],
    properties: Mapping[str, Any],
    segment_m: float,
    direction: str,
) -> float:
    if profile.get("routing_mode") == "distance":
        return segment_m

    edge_kind = properties.get("edge_kind") or "footway"
    penalties = (profile.get("cost") or {}).get("event_penalties_m") or {}
    event_penalty = penalties.get(edge_kind)
    if event_penalty is None:
        return math.inf

    suffix = "fwd" if direction == "forward" else "bwd"
    if properties.get(f"{profile_id}_allow_{suffix}") is False:
        return math.inf
    try:
        grade = float(properties.get(f"{profile_id}_grade_{suffix}"))
    except (TypeError, ValueError):
        return math.inf
    multiplier = _grade_multiplier(profile, grade)
    if not math.isfinite(grade) or grade <= 0 or multiplier is None:
        return math.inf

    try:
        feature_length = float(properties.get("length_m"))
    except (TypeError, ValueError):
        feature_length = segment_m
    if not math.isfinite(feature_length):
        feature_length = segment_m
    feature_length = max(feature_length, segment_m)
    proportional_penalty = float(event_penalty) * segment_m / feature_length
    return segment_m * multiplier + proportional_penalty


def _array_bytes(typecode: str, values: Iterable[int | float]) -> bytes:
    result = array(typecode, values)
    if sys.byteorder != "little":
        result.byteswap()
    return result.tobytes()


def _grid_dimensions(
    segment_count: int,
    bounds: tuple[float, float, float, float],
) -> tuple[int, int]:
    """Choose a bounded grid with roughly twelve segments per cell."""

    min_lon, min_lat, max_lon, max_lat = bounds
    mid_lat = math.radians((min_lat + max_lat) / 2.0)
    width = max((max_lon - min_lon) * max(math.cos(mid_lat), 1e-6), 1e-9)
    height = max(max_lat - min_lat, 1e-9)
    aspect = width / height
    target_cells = max(1, math.ceil(segment_count / 12.0))
    cols = math.ceil(math.sqrt(target_cells * aspect))
    rows = math.ceil(target_cells / max(cols, 1))
    return min(256, max(1, cols)), min(256, max(1, rows))


def _cell_coordinate(
    value: float, minimum: float, maximum: float, cells: int
) -> int:
    if cells <= 1 or maximum <= minimum:
        return 0
    return min(cells - 1, max(0, int((value - minimum) / (maximum - minimum) * cells)))


def build_binary_graph(
    routing_rows: Sequence[Mapping[str, Any]],
    profile_payload: Mapping[str, Any],
    output_path: str | os.PathLike[str],
    *,
    tolerance: float = TOPOLOGY_TOLERANCE,
) -> dict[str, Any]:
    """Build a versioned typed-array graph and return its audit metadata."""

    if tolerance <= 0:
        raise ValueError("topology tolerance must be positive")
    if not routing_rows:
        raise ValueError("routing rows must contain features")

    profile_order = _profile_order(profile_payload)
    profiles = profile_payload["profiles"]
    nodes: dict[tuple[int, int], int] = {}
    longitudes: list[float] = []
    latitudes: list[float] = []
    edge_weights: dict[tuple[int, int], tuple[float, ...]] = {}

    def node_id(coordinate: Sequence[Any]) -> int:
        if len(coordinate) < 2:
            raise ValueError("routing coordinates must contain longitude and latitude")
        lon, lat = float(coordinate[0]), float(coordinate[1])
        if not math.isfinite(lon) or not math.isfinite(lat):
            raise ValueError("routing coordinates must be finite")
        # JavaScript's Math.round chooses the integer toward +Infinity at a
        # half step; Python's built-in round uses ties-to-even instead.
        key = (
            math.floor(lon / tolerance + 0.5),
            math.floor(lat / tolerance + 0.5),
        )
        identifier = nodes.get(key)
        if identifier is None:
            identifier = len(nodes)
            nodes[key] = identifier
            longitudes.append(lon)
            latitudes.append(lat)
        else:
            # geojson-path-finder retains the last coordinate assigned to a
            # rounded topology key.  Preserve that behaviour during migration.
            longitudes[identifier] = lon
            latitudes[identifier] = lat
        return identifier

    # PathFinder creates the complete rounded vertex table first, with the last
    # raw coordinate winning, and only then calculates edge weights. Use the
    # same two passes so migration cannot alter costs around near-equal nodes.
    for row in routing_rows:
        if not isinstance(row, Mapping):
            continue
        geometry = row.get("geometry")
        for coordinates in _line_coordinates(geometry):
            for coordinate in coordinates:
                node_id(coordinate)

    def existing_node_id(coordinate: Sequence[Any]) -> int:
        lon, lat = float(coordinate[0]), float(coordinate[1])
        key = (
            math.floor(lon / tolerance + 0.5),
            math.floor(lat / tolerance + 0.5),
        )
        return nodes[key]

    for row in routing_rows:
        if not isinstance(row, Mapping):
            continue
        geometry = row.get("geometry")
        for coordinates in _line_coordinates(geometry):
            if len(coordinates) < 2:
                continue
            previous_id = existing_node_id(coordinates[0])
            for coordinate in coordinates[1:]:
                current_id = existing_node_id(coordinate)
                if current_id == previous_id:
                    previous_id = current_id
                    continue
                segment_m = _haversine_m(
                    (longitudes[previous_id], latitudes[previous_id]),
                    (longitudes[current_id], latitudes[current_id]),
                )
                forward = tuple(
                    _directional_weight(
                        profile_id,
                        profiles[profile_id],
                        row,
                        segment_m,
                        "forward",
                    )
                    for profile_id in profile_order
                )
                backward = tuple(
                    _directional_weight(
                        profile_id,
                        profiles[profile_id],
                        row,
                        segment_m,
                        "backward",
                    )
                    for profile_id in profile_order
                )
                # Duplicate graph edges intentionally use last-write-wins,
                # matching the topology reducer used by the old client.
                edge_weights[(previous_id, current_id)] = forward
                edge_weights[(current_id, previous_id)] = backward
                previous_id = current_id

    if not edge_weights:
        raise ValueError("routing features did not produce any graph edges")

    directed_items = sorted(edge_weights.items())
    adjacency_offsets = [0] * (len(nodes) + 1)
    targets: list[int] = []
    weights_by_profile = [array("f") for _ in profile_order]
    cursor = 0
    for source in range(len(nodes)):
        adjacency_offsets[source] = cursor
        while cursor < len(directed_items) and directed_items[cursor][0][0] == source:
            (_edge_source, target), weights = directed_items[cursor]
            targets.append(target)
            for profile_index, weight in enumerate(weights):
                weights_by_profile[profile_index].append(weight)
            cursor += 1
    adjacency_offsets[len(nodes)] = cursor

    segment_pairs = sorted(
        {(min(source, target), max(source, target)) for source, target in edge_weights}
    )
    segment_a = [pair[0] for pair in segment_pairs]
    segment_b = [pair[1] for pair in segment_pairs]

    bounds = (
        min(longitudes),
        min(latitudes),
        max(longitudes),
        max(latitudes),
    )
    grid_cols, grid_rows = _grid_dimensions(len(segment_pairs), bounds)
    cells: list[list[int]] = [[] for _ in range(grid_cols * grid_rows)]
    min_lon, min_lat, max_lon, max_lat = bounds
    for segment_id, (left, right) in enumerate(segment_pairs):
        left_lon, left_lat = longitudes[left], latitudes[left]
        right_lon, right_lat = longitudes[right], latitudes[right]
        first_col = _cell_coordinate(min(left_lon, right_lon), min_lon, max_lon, grid_cols)
        last_col = _cell_coordinate(max(left_lon, right_lon), min_lon, max_lon, grid_cols)
        first_row = _cell_coordinate(min(left_lat, right_lat), min_lat, max_lat, grid_rows)
        last_row = _cell_coordinate(max(left_lat, right_lat), min_lat, max_lat, grid_rows)
        for row in range(first_row, last_row + 1):
            offset = row * grid_cols
            for col in range(first_col, last_col + 1):
                cells[offset + col].append(segment_id)

    cell_offsets = [0]
    cell_segments: list[int] = []
    for cell in cells:
        cell_segments.extend(cell)
        cell_offsets.append(len(cell_segments))

    sections = {
        "longitudes": _array_bytes("d", longitudes),
        "latitudes": _array_bytes("d", latitudes),
        "adjacency_offsets": _array_bytes("I", adjacency_offsets),
        "targets": _array_bytes("I", targets),
        "weights": b"".join(
            values.tobytes()
            if sys.byteorder == "little"
            else _array_bytes("f", values)
            for values in weights_by_profile
        ),
        "segment_a": _array_bytes("I", segment_a),
        "segment_b": _array_bytes("I", segment_b),
        "cell_offsets": _array_bytes("I", cell_offsets),
        "cell_segments": _array_bytes("I", cell_segments),
    }

    header = bytearray(HEADER_BYTES)
    header[:8] = MAGIC
    struct.pack_into("<I", header, 8, SCHEMA_VERSION)
    struct.pack_into("<I", header, 12, HEADER_BYTES)
    counts = {
        "node_count": len(nodes),
        "directed_edge_count": len(directed_items),
        "profile_count": len(profile_order),
        "segment_count": len(segment_pairs),
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "cell_membership_count": len(cell_segments),
    }
    for name, offset in _COUNT_OFFSETS.items():
        struct.pack_into("<I", header, offset, counts[name])

    file_offset = HEADER_BYTES
    for name, header_offset in _ARRAY_OFFSETS.items():
        struct.pack_into("<Q", header, header_offset, file_offset)
        file_offset += len(sections[name])
    struct.pack_into("<5d", header, 136, *bounds, tolerance)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(header)
            for name in _ARRAY_OFFSETS:
                temporary.write(sections[name])
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)

    digest_builder = hashlib.sha256()
    with destination.open("rb") as graph_file:
        for chunk in iter(lambda: graph_file.read(1024 * 1024), b""):
            digest_builder.update(chunk)
    digest = digest_builder.hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "filename": destination.name,
        "byte_size": destination.stat().st_size,
        "sha256": digest,
        **counts,
        "profile_order": profile_order,
        "bounds": list(bounds),
        "topology_tolerance": tolerance,
        "spatial_index": "uniform_grid",
    }


def read_graph_header(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read and validate the public header, primarily for audits and tests."""

    with open(path, "rb") as source:
        header = source.read(HEADER_BYTES)
    if len(header) < HEADER_BYTES:
        raise ValueError("routing graph is shorter than its fixed header")
    if header[:8] != MAGIC:
        raise ValueError("routing graph has an unknown magic value")
    version = struct.unpack_from("<I", header, 8)[0]
    header_bytes = struct.unpack_from("<I", header, 12)[0]
    if version != SCHEMA_VERSION or header_bytes != HEADER_BYTES:
        raise ValueError("routing graph schema is not supported")
    result: dict[str, Any] = {
        "schema_version": version,
        "header_bytes": header_bytes,
    }
    for name, offset in _COUNT_OFFSETS.items():
        result[name] = struct.unpack_from("<I", header, offset)[0]
    for name, offset in _ARRAY_OFFSETS.items():
        result[f"{name}_offset"] = struct.unpack_from("<Q", header, offset)[0]
    values = struct.unpack_from("<5d", header, 136)
    result["bounds"] = list(values[:4])
    result["topology_tolerance"] = values[4]
    return result

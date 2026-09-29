"""Elevation-provider hierarchy and robust terrain-slope estimation.

OSM ``incline=*`` remains authoritative and is parsed in ``routing.grading``.
This module supplies a geometric estimate when a numeric mapped incline is not
available. Heavy geospatial dependencies are imported lazily so profile rules
and their validators remain usable in lightweight environments.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any

from .profile_rules import DEFAULT_ELEVATION_CONFIG, SOURCE_CONFIDENCE


COPERNICUS_BASE_URLS = {
    30: "https://copernicus-dem-30m.s3.amazonaws.com",
    90: "https://copernicus-dem-90m.s3.amazonaws.com",
}


@dataclass(frozen=True)
class SlopeEstimate:
    percent: float | None
    source: str
    confidence: int
    resolution_m: float | None = None
    sample_count: int = 0
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def copernicus_tile_name(
    latitude: float, longitude: float, resolution_m: int = 30
) -> str:
    """Return the AWS Copernicus COG tile identifier for a coordinate."""

    if resolution_m not in COPERNICUS_BASE_URLS:
        raise ValueError("Copernicus resolution must be 30 or 90 metres")
    south = math.floor(latitude)
    west = math.floor(longitude)
    lat_token = f"N{south:02d}" if south >= 0 else f"S{abs(south):02d}"
    lon_token = f"E{west:03d}" if west >= 0 else f"W{abs(west):03d}"
    arc_seconds = 10 if resolution_m == 30 else 30
    return (
        f"Copernicus_DSM_COG_{arc_seconds}_{lat_token}_00_"
        f"{lon_token}_00_DEM"
    )


def copernicus_tile_url(
    latitude: float, longitude: float, resolution_m: int = 30
) -> str:
    tile = copernicus_tile_name(latitude, longitude, resolution_m)
    return f"{COPERNICUS_BASE_URLS[resolution_m]}/{tile}/{tile}.tif"


def robust_slope_percent(
    distances_m: list[float], elevations_m: list[float]
) -> float | None:
    """Estimate slope with a small Theil–Sen median-of-pairs calculation."""

    samples = []
    for distance, elevation in zip(distances_m, elevations_m):
        distance_number = _finite_float(distance)
        elevation_number = _finite_float(elevation)
        if distance_number is not None and elevation_number is not None:
            samples.append((distance_number, elevation_number))
    if len(samples) < 2:
        return None

    slopes = []
    for left in range(len(samples)):
        for right in range(left + 1, len(samples)):
            run = samples[right][0] - samples[left][0]
            if abs(run) > 1e-9:
                slopes.append(
                    (samples[right][1] - samples[left][1]) / run * 100
                )
    return median(slopes) if slopes else None


def _utm_crs_for_lonlat(longitude: float, latitude: float) -> str:
    zone = max(1, min(60, int((longitude + 180) // 6) + 1))
    epsg = 32600 + zone if latitude >= 0 else 32700 + zone
    return f"EPSG:{epsg}"


import functools
from pyproj import Transformer

@functools.lru_cache(maxsize=128)
def get_transformer(from_crs: str, to_crs: str) -> Transformer:
    return Transformer.from_crs(from_crs, to_crs, always_xy=True)

def sample_positions(
    geometry: Any, minimum_baseline_m: float, sample_count: int
) -> tuple[list[tuple[float, float]], list[float]]:
    """Create lon/lat samples along a line, extending short lines by tangents."""

    if sample_count < 2:
        raise ValueError("sample_count must be at least two")

    from shapely.geometry import LineString
    from shapely.ops import transform

    if geometry is None or geometry.is_empty or geometry.geom_type != "LineString":
        raise ValueError("slope estimation requires a non-empty LineString")

    centroid = geometry.centroid
    metric_crs = _utm_crs_for_lonlat(centroid.x, centroid.y)
    to_metric = get_transformer("EPSG:4326", metric_crs)
    to_lonlat = get_transformer(metric_crs, "EPSG:4326")
    line = transform(to_metric.transform, geometry)
    coordinates = list(line.coords)
    if len(coordinates) < 2 or line.length <= 0:
        raise ValueError("slope estimation requires a line with length")

    extension = max(0.0, minimum_baseline_m - line.length) / 2

    def extend(point: tuple[float, float], neighbour: tuple[float, float], amount: float):
        dx = point[0] - neighbour[0]
        dy = point[1] - neighbour[1]
        norm = math.hypot(dx, dy)
        if norm <= 0:
            return point
        return (point[0] + dx / norm * amount, point[1] + dy / norm * amount)

    start = extend(coordinates[0], coordinates[1], extension)
    end = extend(coordinates[-1], coordinates[-2], extension)
    extended = LineString([start, *coordinates[1:-1], end])
    distances = [
        extended.length * index / (sample_count - 1)
        for index in range(sample_count)
    ]
    metric_points = [extended.interpolate(distance) for distance in distances]
    lonlat_points = [
        to_lonlat.transform(point.x, point.y) for point in metric_points
    ]
    return lonlat_points, distances


class RasterElevationProvider:
    """Base provider capable of sampling one or more rasters."""

    source_name = "raster"
    default_confidence = 50
    resolution_m: float | None = None

    def __init__(self, config: dict[str, Any], request_timeout_seconds: int = 120):
        self.config = dict(config)
        self.request_timeout_seconds = request_timeout_seconds
        self.minimum_baseline_m = float(config.get("minimum_baseline_m", 30))
        self.sample_count = int(config.get("sample_count", 7))
        self.max_abs_slope_percent = float(
            config.get("max_abs_slope_percent", 100)
        )

    def sample(self, points_lonlat: list[tuple[float, float]]) -> list[float]:
        raise NotImplementedError

    def estimate(self, geometry: Any) -> SlopeEstimate:
        try:
            points, distances = sample_positions(
                geometry, self.minimum_baseline_m, self.sample_count
            )
            elevations = self.sample(points)
            slope = robust_slope_percent(distances, elevations)
        except Exception as exc:
            return SlopeEstimate(
                None,
                self.source_name,
                0,
                self.resolution_m,
                note=f"{type(exc).__name__}: {exc}",
            )

        valid_count = sum(
            _finite_float(value) is not None for value in elevations
        )
        if slope is None:
            return SlopeEstimate(
                None,
                self.source_name,
                0,
                self.resolution_m,
                valid_count,
                "insufficient valid elevation samples",
            )
        if abs(slope) > self.max_abs_slope_percent:
            return SlopeEstimate(
                None,
                self.source_name,
                0,
                self.resolution_m,
                valid_count,
                "slope rejected as implausible for this provider",
            )
        completeness = valid_count / max(1, self.sample_count)
        confidence = round(
            float(self.config.get("confidence", self.default_confidence))
            * completeness
        )
        return SlopeEstimate(
            round(slope, 3),
            self.source_name,
            confidence,
            self.resolution_m,
            valid_count,
        )


class CopernicusDEMProvider(RasterElevationProvider):
    """Cached AWS Open Data provider for a Copernicus global DEM instance."""

    def __init__(self, config: dict[str, Any], request_timeout_seconds: int = 120):
        super().__init__(config, request_timeout_seconds)
        self.resolution_m = int(config.get("resolution_m", 30))
        if self.resolution_m not in COPERNICUS_BASE_URLS:
            raise ValueError("Copernicus resolution must be 30 or 90 metres")
        self.source_name = f"copernicus_glo{self.resolution_m}"
        self.default_confidence = SOURCE_CONFIDENCE[self.source_name]
        self.cache_dir = Path(
            config.get(
                "cache_dir",
                f".cache/oswm/elevation/{self.source_name}",
            )
        )
        self._failed_tiles: set[str] = set()
        self._datasets: dict[Path, Any] = {}

    def _local_tile(self, latitude: float, longitude: float) -> Path:
        import requests

        tile = copernicus_tile_name(
            latitude, longitude, int(self.resolution_m)
        )
        if tile in self._failed_tiles:
            raise RuntimeError(f"Copernicus tile unavailable during this run: {tile}")
        target = self.cache_dir / f"{tile}.tif"
        if target.exists() and target.stat().st_size > 0:
            return target

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with requests.get(
                copernicus_tile_url(
                    latitude, longitude, int(self.resolution_m)
                ),
                stream=True,
                timeout=self.request_timeout_seconds,
            ) as response:
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(
                    dir=self.cache_dir,
                    prefix=f"{tile}.",
                    suffix=".tmp",
                    delete=False,
                ) as handle:
                    temporary = Path(handle.name)
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
            os.replace(temporary, target)
        except Exception:
            self._failed_tiles.add(tile)
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise
        return target

    def sample(self, points_lonlat: list[tuple[float, float]]) -> list[float]:
        import rasterio

        indexed_by_tile: dict[Path, list[tuple[int, tuple[float, float]]]] = {}
        for index, point in enumerate(points_lonlat):
            path = self._local_tile(point[1], point[0])
            indexed_by_tile.setdefault(path, []).append((index, point))

        values = [float("nan")] * len(points_lonlat)
        for path, indexed_points in indexed_by_tile.items():
            dataset = self._datasets.get(path)
            if dataset is None or dataset.closed:
                dataset = rasterio.open(path)
                self._datasets[path] = dataset
            samples = dataset.sample([point for _index, point in indexed_points])
            nodata = dataset.nodata
            for (index, _point), sample in zip(indexed_points, samples):
                value = float(sample[0])
                if nodata is None or value != nodata:
                    values[index] = value
        return values

    def close(self) -> None:
        for dataset in self._datasets.values():
            dataset.close()
        self._datasets.clear()


class CopernicusGLO30Provider(CopernicusDEMProvider):
    source_name = "copernicus_glo30"
    default_confidence = SOURCE_CONFIDENCE["copernicus_glo30"]
    resolution_m = 30

    def __init__(self, config: dict[str, Any], request_timeout_seconds: int = 120):
        super().__init__({**config, "resolution_m": 30}, request_timeout_seconds)


class CopernicusGLO90Provider(CopernicusDEMProvider):
    source_name = "copernicus_glo90"
    default_confidence = SOURCE_CONFIDENCE["copernicus_glo90"]
    resolution_m = 90

    def __init__(self, config: dict[str, Any], request_timeout_seconds: int = 120):
        super().__init__({**config, "resolution_m": 90}, request_timeout_seconds)


class COGElevationProvider(RasterElevationProvider):
    source_name = "configured_cog"
    default_confidence = SOURCE_CONFIDENCE["regional_dtm"]

    def __init__(self, config: dict[str, Any], request_timeout_seconds: int = 120):
        super().__init__(config, request_timeout_seconds)
        self.path = config.get("path") or config.get("url")
        if not self.path:
            raise ValueError("a configured COG provider requires path or url")
        self.source_name = str(config.get("source_name", "configured_cog"))
        self.resolution_m = config.get("resolution_m")

    def sample(self, points_lonlat: list[tuple[float, float]]) -> list[float]:
        import rasterio
        from pyproj import Transformer

        with rasterio.open(self.path) as dataset:
            if dataset.crs and str(dataset.crs).upper() != "EPSG:4326":
                transformer = Transformer.from_crs(
                    "EPSG:4326", dataset.crs, always_xy=True
                )
                sample_points = [
                    transformer.transform(longitude, latitude)
                    for longitude, latitude in points_lonlat
                ]
            else:
                sample_points = points_lonlat
            nodata = dataset.nodata
            values = []
            for sample in dataset.sample(sample_points):
                value = float(sample[0])
                values.append(
                    float("nan") if nodata is not None and value == nodata else value
                )
            return values


class ElevationResolver:
    """Try configured raster providers in descending priority order."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = dict(DEFAULT_ELEVATION_CONFIG if config is None else config)
        timeout = int(self.config.get("request_timeout_seconds", 120))
        providers = []
        if self.config.get("enabled", True):
            provider_configs = sorted(
                self.config.get("providers", []),
                key=lambda item: item.get("priority", 0),
                reverse=True,
            )
            for provider_config in provider_configs:
                provider_type = provider_config.get("type")
                if provider_type == "copernicus_glo30":
                    providers.append(CopernicusGLO30Provider(provider_config, timeout))
                elif provider_type == "copernicus_glo90":
                    providers.append(CopernicusGLO90Provider(provider_config, timeout))
                elif provider_type in {"cog", "local_cog"}:
                    providers.append(COGElevationProvider(provider_config, timeout))
                else:
                    raise ValueError(
                        f"unsupported elevation provider: {provider_type!r}"
                    )
        self.providers = providers

    def estimate(self, geometry: Any, incline_value: Any = None) -> SlopeEstimate:
        for provider in self.providers:
            estimate = provider.estimate(geometry)
            if estimate.percent is None:
                continue

            # Qualitative OSM direction is weaker than a numeric incline but can
            # disambiguate the sign of a terrain-derived magnitude.
            qualitative = (
                str(incline_value).strip().lower()
                if incline_value is not None
                else ""
            )
            if qualitative in {"up", "uphill"}:
                estimate = SlopeEstimate(
                    abs(estimate.percent),
                    estimate.source,
                    min(estimate.confidence, SOURCE_CONFIDENCE["osm_qualitative"]),
                    estimate.resolution_m,
                    estimate.sample_count,
                    "direction constrained by qualitative OSM incline",
                )
            elif qualitative in {"down", "downhill"}:
                estimate = SlopeEstimate(
                    -abs(estimate.percent),
                    estimate.source,
                    min(estimate.confidence, SOURCE_CONFIDENCE["osm_qualitative"]),
                    estimate.resolution_m,
                    estimate.sample_count,
                    "direction constrained by qualitative OSM incline",
                )
            return estimate
        return SlopeEstimate(None, "missing", 0, note="no provider produced a slope")

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.config, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]

    def close(self) -> None:
        for provider in self.providers:
            close = getattr(provider, "close", None)
            if callable(close):
                close()


def slope_cache_key(
    geometry: Any, incline_value: Any, provider_fingerprint: str
) -> str:
    geometry_bytes = geometry.wkb if geometry is not None else b""
    payload = (
        geometry_bytes
        + str(incline_value).encode("utf-8")
        + provider_fingerprint.encode("ascii")
    )
    return hashlib.sha256(payload).hexdigest()


def load_slope_cache(path: str | os.PathLike[str]) -> dict[str, dict[str, Any]]:
    cache_path = Path(path)
    if not cache_path.exists():
        return {}
    try:
        with cache_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_slope_cache(
    path: str | os.PathLike[str], cache: dict[str, dict[str, Any]]
) -> None:
    cache_path = Path(path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=cache_path.parent,
        prefix=f"{cache_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(cache, handle, sort_keys=True, separators=(",", ":"))
        temporary = Path(handle.name)
    os.replace(temporary, cache_path)

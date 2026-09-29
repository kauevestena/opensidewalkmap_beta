"""Generate contextual terrain-difficulty overlays from global AWS DEM tiles."""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path
from typing import Any

from routing.elevation import (
    CopernicusGLO30Provider,
    CopernicusGLO90Provider,
)


COPERNICUS_LICENSE_URL = (
    "https://dataspace.copernicus.eu/explore-data/data-collections/"
    "copernicus-contributing-missions/collections-description/COP-DEM"
)
COPERNICUS_SOURCES = {
    "copernicus_glo30": {
        "title": "Copernicus DEM GLO-30 Public (2021)",
        "resolution_m": 30,
        "source_url": "https://registry.opendata.aws/copernicus-dem/",
        "license": "Copernicus DEM free licence",
        "license_url": COPERNICUS_LICENSE_URL,
        "attribution": (
            "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 "
            "and © Airbus Defence and Space GmbH 2014–2018 provided under "
            "COPERNICUS by the European Union and ESA; all rights reserved."
        ),
    },
    "copernicus_glo90": {
        "title": "Copernicus DEM GLO-90 (2021)",
        "resolution_m": 90,
        "source_url": "https://registry.opendata.aws/copernicus-dem/",
        "license": "Copernicus DEM free licence",
        "license_url": COPERNICUS_LICENSE_URL,
        "attribution": (
            "Produced using Copernicus WorldDEM-90 © DLR e.V. 2010–2014 "
            "and © Airbus Defence and Space GmbH 2014–2018 provided under "
            "COPERNICUS by the European Union and ESA; all rights reserved."
        ),
    },
}

TERRAIN_THRESHOLDS = {
    "pedestrian": [5.0, 8.33, 12.5, 20.0],
    "wheelchair": [2.0, 5.0, 8.33, 12.5],
    "blind": [5.0, 8.33, 12.5, 20.0],
    "elderly": [2.0, 5.0, 8.33, 12.5],
}

_RGBA = {
    0: (0, 0, 0, 0),
    1: (254, 224, 139, 105),
    2: (253, 174, 97, 145),
    3: (244, 109, 67, 180),
    4: (165, 0, 38, 215),
}


def classify_terrain_slope(
    slope_percent: Any, thresholds: list[float]
):
    """Classify unsigned slope potential into hazard severity 0..4."""

    import numpy as np

    slope = np.asarray(slope_percent, dtype="float32")
    result = np.zeros(slope.shape, dtype="uint8")
    for severity, threshold in enumerate(thresholds, start=1):
        result[slope > threshold] = severity
    result[~np.isfinite(slope)] = 0
    return result


def _smooth_nan(array, sigma: float):
    import numpy as np

    if sigma <= 0:
        return array
    radius = max(1, int(math.ceil(sigma * 3)))
    offsets = np.arange(-radius, radius + 1, dtype="float32")
    kernel = np.exp(-(offsets**2) / (2 * sigma**2))
    kernel /= kernel.sum()
    valid = np.isfinite(array).astype("float32")
    values = np.nan_to_num(array, nan=0.0).astype("float32")

    def convolve(data, axis):
        return np.apply_along_axis(
            lambda row: np.convolve(row, kernel, mode="same"), axis, data
        )

    weighted = convolve(convolve(values, 1), 0)
    weights = convolve(convolve(valid, 1), 0)
    return np.divide(
        weighted,
        weights,
        out=np.full_like(weighted, np.nan),
        where=weights > 1e-6,
    )


def _candidate_tiles(bounds: tuple[float, float, float, float]):
    minx, miny, maxx, maxy = bounds
    for south in range(math.floor(miny), math.ceil(maxy)):
        for west in range(math.floor(minx), math.ceil(maxx)):
            yield south + 0.5, west + 0.5


def _provider_from_config(config: dict[str, Any], timeout: int):
    provider_type = config.get("type")
    if provider_type == "copernicus_glo30":
        return CopernicusGLO30Provider(config, timeout)
    if provider_type == "copernicus_glo90":
        return CopernicusGLO90Provider(config, timeout)
    return None


def _read_provider_window(
    provider,
    bounds: tuple[float, float, float, float],
    max_dimension: int,
):
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.merge import merge

    paths = [
        provider._local_tile(latitude, longitude)
        for latitude, longitude in _candidate_tiles(bounds)
    ]
    datasets = [rasterio.open(path) for path in paths]
    try:
        native_x = min(abs(dataset.transform.a) for dataset in datasets)
        native_y = min(abs(dataset.transform.e) for dataset in datasets)
        estimated_width = (bounds[2] - bounds[0]) / native_x
        estimated_height = (bounds[3] - bounds[1]) / native_y
        scale = max(1.0, estimated_width / max_dimension, estimated_height / max_dimension)
        data, transform = merge(
            datasets,
            bounds=bounds,
            res=(native_x * scale, native_y * scale),
            nodata=np.nan,
            dtype="float32",
            resampling=Resampling.bilinear,
        )
        return data[0], transform
    finally:
        for dataset in datasets:
            dataset.close()


def _atomic_png(path: Path, rgba) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp.png",
        delete=False,
    )
    temporary = Path(handle.name)
    handle.close()
    try:
        Image.fromarray(rgba, mode="RGBA").save(temporary, "PNG", optimize=True)
        with Image.open(temporary) as check:
            check.verify()
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def generate_terrain_overlays(
    bounds: tuple[float, float, float, float],
    elevation_config: dict[str, Any],
    terrain_config: dict[str, Any],
    output_dir: str | os.PathLike[str],
    boundary_geojson_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Render one transparent contextual terrain layer per user profile."""

    import numpy as np

    if not terrain_config.get("enabled", True):
        return {
            "schema_version": 1,
            "available": False,
            "reason": "terrain overlay disabled by node configuration",
        }

    timeout = int(elevation_config.get("request_timeout_seconds", 120))
    provider_configs = sorted(
        elevation_config.get("providers", []),
        key=lambda item: item.get("priority", 0),
        reverse=True,
    )
    max_dimension = int(terrain_config.get("max_dimension", 1600))
    sigma = float(terrain_config.get("smoothing_sigma_pixels", 3.0))
    failures: list[str] = []
    provider = None
    elevation = transform = None
    for config in provider_configs:
        candidate = _provider_from_config(config, timeout)
        if candidate is None:
            continue
        try:
            elevation, transform = _read_provider_window(
                candidate, bounds, max_dimension
            )
        except Exception as exc:
            failures.append(
                f"{candidate.source_name}: {type(exc).__name__}: {exc}"
            )
            continue
        provider = candidate
        break

    if provider is None or elevation is None or transform is None:
        return {
            "schema_version": 1,
            "available": False,
            "reason": "no global elevation provider covered this node",
            "provider_failures": failures,
        }

    if boundary_geojson_path is not None and os.path.exists(boundary_geojson_path):
        import json
        from rasterio.features import geometry_mask

        with open(boundary_geojson_path, "r", encoding="utf-8") as f:
            boundary_data = json.load(f)
        
        geoms = []
        if boundary_data.get("type") == "FeatureCollection":
            for feat in boundary_data.get("features", []):
                if "geometry" in feat:
                    geoms.append(feat["geometry"])
        elif boundary_data.get("type") in ("Polygon", "MultiPolygon"):
            geoms.append(boundary_data)
        
        if geoms:
            mask = geometry_mask(
                geoms,
                out_shape=elevation.shape,
                transform=transform,
                invert=False
            )
            elevation[mask] = np.nan

    elevation = _smooth_nan(elevation, sigma)
    latitude = (bounds[1] + bounds[3]) / 2
    x_metres = abs(transform.a) * 111_320 * max(
        0.01, math.cos(math.radians(latitude))
    )
    y_metres = abs(transform.e) * 110_574
    gradient_y, gradient_x = np.gradient(elevation, y_metres, x_metres)
    slope_percent = np.hypot(gradient_x, gradient_y) * 100

    output_path = Path(output_dir)
    profile_metadata = {}
    for profile_id, thresholds in TERRAIN_THRESHOLDS.items():
        severity = classify_terrain_slope(slope_percent, thresholds)
        rgba = np.zeros((*severity.shape, 4), dtype="uint8")
        for level, color in _RGBA.items():
            rgba[severity == level] = color
        filename = f"terrain_{profile_id}.png"
        _atomic_png(output_path / filename, rgba)
        profile_metadata[profile_id] = {
            "path": f"data/hazard_analysis/{filename}",
            "thresholds_percent": thresholds,
        }

    source = COPERNICUS_SOURCES[provider.source_name]
    return {
        "schema_version": 1,
        "available": True,
        "title": "Terrain difficulty potential",
        "description": (
            "Contextual unsigned slope potential derived from a global digital "
            "surface model. It is not a measurement of sidewalk or cross slope."
        ),
        "source_name": provider.source_name,
        "source_title": source["title"],
        "source_url": source["source_url"],
        "source_attribution": source["attribution"],
        "license": source["license"],
        "license_url": source["license_url"],
        "resolution_m": source["resolution_m"],
        "bounds": list(bounds),
        "coordinates": [
            [bounds[0], bounds[3]],
            [bounds[2], bounds[3]],
            [bounds[2], bounds[1]],
            [bounds[0], bounds[1]],
        ],
        "width": int(elevation.shape[1]),
        "height": int(elevation.shape[0]),
        "directionality": "unsigned contextual potential",
        "cross_slope_included": False,
        "smoothing_sigma_pixels": sigma,
        "profiles": profile_metadata,
        "provider_failures": failures,
    }

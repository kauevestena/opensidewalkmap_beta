import {
    DEFAULT_UNKNOWN_VALUE,
    deduplicateFeatures,
    featureIdentity,
    normalizeUnknown,
    summarizeCategoricalValues,
    summarizeNumericValues,
} from "../snapshot/snapshot_stats.js";

const EARTH_RADIUS_KM = 6371.0088;

function rounded(value, digits = 6) {
    const power = 10 ** digits;
    return Math.round((value + Number.EPSILON) * power) / power;
}

function toRadians(value) {
    return Number(value) * Math.PI / 180;
}

function haversineKm(left, right) {
    const lat1 = toRadians(left[1]);
    const lat2 = toRadians(right[1]);
    const deltaLat = lat2 - lat1;
    const deltaLon = toRadians(right[0] - left[0]);
    const haversine = Math.sin(deltaLat / 2) ** 2
        + Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
    return 2 * EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(haversine)));
}

export function normalizeMapBounds(bounds) {
    if (!bounds) return null;
    if (Array.isArray(bounds) && bounds.length === 4) {
        return {
            west: Number(bounds[0]),
            south: Number(bounds[1]),
            east: Number(bounds[2]),
            north: Number(bounds[3]),
        };
    }
    if (Array.isArray(bounds) && bounds.length === 2) {
        return {
            west: Number(bounds[0][0]),
            south: Number(bounds[0][1]),
            east: Number(bounds[1][0]),
            north: Number(bounds[1][1]),
        };
    }
    if (typeof bounds.getWest === "function") {
        return {
            west: Number(bounds.getWest()),
            south: Number(bounds.getSouth()),
            east: Number(bounds.getEast()),
            north: Number(bounds.getNorth()),
        };
    }
    if (bounds._sw && bounds._ne) {
        return {
            west: Number(bounds._sw.lng),
            south: Number(bounds._sw.lat),
            east: Number(bounds._ne.lng),
            north: Number(bounds._ne.lat),
        };
    }
    return null;
}

function clipSegmentToBounds(start, end, bounds) {
    if (!bounds || bounds.west > bounds.east) return [start, end];
    const x0 = Number(start[0]);
    const y0 = Number(start[1]);
    const dx = Number(end[0]) - x0;
    const dy = Number(end[1]) - y0;
    let lower = 0;
    let upper = 1;
    const tests = [
        [-dx, x0 - bounds.west],
        [dx, bounds.east - x0],
        [-dy, y0 - bounds.south],
        [dy, bounds.north - y0],
    ];

    for (const [direction, distance] of tests) {
        if (direction === 0 && distance < 0) return null;
        if (direction === 0) continue;
        const ratio = distance / direction;
        if (direction < 0) {
            if (ratio > upper) return null;
            lower = Math.max(lower, ratio);
        } else {
            if (ratio < lower) return null;
            upper = Math.min(upper, ratio);
        }
    }

    return [
        [x0 + lower * dx, y0 + lower * dy],
        [x0 + upper * dx, y0 + upper * dy],
    ];
}

function coordinateLines(geometry) {
    if (!geometry) return [];
    if (geometry.type === "LineString") return [geometry.coordinates || []];
    if (geometry.type === "MultiLineString") return geometry.coordinates || [];
    if (geometry.type === "GeometryCollection") {
        return (geometry.geometries || []).flatMap(coordinateLines);
    }
    return [];
}

export function lineLengthKmInBounds(geometry, bounds) {
    const normalizedBounds = normalizeMapBounds(bounds);
    let lengthKm = 0;
    coordinateLines(geometry).forEach((line) => {
        for (let index = 1; index < line.length; index += 1) {
            const clipped = clipSegmentToBounds(line[index - 1], line[index], normalizedBounds);
            if (clipped) lengthKm += haversineKm(clipped[0], clipped[1]);
        }
    });
    return rounded(lengthKm);
}

function geometryFingerprint(feature) {
    try {
        return JSON.stringify(feature?.geometry || null);
    } catch (_error) {
        return "unserializable-geometry";
    }
}

export function deduplicateRenderedFragments(features = []) {
    const fragments = new Map();
    features.forEach((feature, index) => {
        const key = `${featureIdentity(feature, index)}:${geometryFingerprint(feature)}`;
        if (!fragments.has(key)) fragments.set(key, feature);
    });
    return [...fragments.values()];
}

function valueFromFeature(feature, theme) {
    if (theme.attribute === "__layer__") {
        return feature?.sourceLayer
            || feature?.layer?.["source-layer"]
            || feature?.layer?.id
            || DEFAULT_UNKNOWN_VALUE;
    }
    return feature?.properties?.[theme.attribute];
}

function visibleAnalyticalLayers(map, layers = []) {
    return layers.filter((layerId) => {
        try {
            return Boolean(map.getLayer(layerId))
                && map.getLayoutProperty(layerId, "visibility") !== "none";
        } catch (_error) {
            return false;
        }
    });
}

function queryVisibleFeatures(map, layers) {
    if (!layers.length) return [];
    try {
        return map.queryRenderedFeatures({ layers }) || [];
    } catch (_error) {
        return [];
    }
}

function categoricalLengthSummary(features, theme, bounds) {
    const fragments = deduplicateRenderedFragments(features);
    const uniqueFeatures = deduplicateFeatures(fragments);
    const values = uniqueFeatures.map((feature) => valueFromFeature(feature, theme));
    const summary = summarizeCategoricalValues(values, {
        unknownValue: theme.unknown_value,
        colors: theme.colors,
        otherColor: theme.other_color,
    });
    const lengthByCategory = new Map();

    fragments.forEach((feature) => {
        const value = String(normalizeUnknown(
            valueFromFeature(feature, theme),
            theme.unknown_value || DEFAULT_UNKNOWN_VALUE,
        ));
        const lengthKm = lineLengthKmInBounds(feature.geometry, bounds);
        lengthByCategory.set(value, (lengthByCategory.get(value) || 0) + lengthKm);
    });

    const unknownValue = theme.unknown_value || DEFAULT_UNKNOWN_VALUE;
    return {
        ...summary,
        lengthFeatureCount: uniqueFeatures.length,
        totalLengthKm: rounded(
            [...lengthByCategory.values()].reduce((total, length) => total + length, 0),
        ),
        unknownLengthKm: rounded(lengthByCategory.get(unknownValue) || 0),
        lengthKmByCategory: Object.fromEntries(
            [...lengthByCategory.entries()]
                .filter(([value]) => value !== unknownValue)
                .map(([value, length]) => [value, rounded(length)]),
        ),
    };
}

function collectSingleTheme(map, theme) {
    const layers = visibleAnalyticalLayers(map, theme.layers);
    const rendered = queryVisibleFeatures(map, layers);
    const bounds = typeof map.getBounds === "function" ? map.getBounds() : null;
    let summary;

    if (theme.kind === "numeric") {
        const unique = deduplicateFeatures(rendered);
        summary = summarizeNumericValues(
            unique.map((feature) => valueFromFeature(feature, theme)),
            {
                unknownValue: theme.unknown_value,
                breaks: theme.breaks,
                colors: theme.colors,
                invalid: theme.invalid,
            },
        );
    } else if (theme.measure === "length") {
        summary = categoricalLengthSummary(rendered, theme, bounds);
    } else {
        const unique = deduplicateFeatures(rendered);
        summary = summarizeCategoricalValues(
            unique.map((feature) => valueFromFeature(feature, theme)),
            {
                unknownValue: theme.unknown_value,
                colors: theme.colors,
                otherColor: theme.other_color,
            },
        );
    }

    return {
        ...summary,
        id: theme.id,
        label: theme.label,
        layers,
        estimated: true,
        source: "visible vector tiles",
    };
}

export function collectViewportThemeStats(map, theme) {
    if (theme.kind === "multi") {
        return {
            id: theme.id,
            kind: "multi",
            label: theme.label,
            panels: (theme.panels || []).map((panel) => collectSingleTheme(map, panel)),
            estimated: true,
            source: "visible vector tiles",
        };
    }
    return collectSingleTheme(map, theme);
}

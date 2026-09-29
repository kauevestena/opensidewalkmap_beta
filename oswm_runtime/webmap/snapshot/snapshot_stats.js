export const DEFAULT_UNKNOWN_VALUE = "?";

export function normalizeUnknown(value, unknownValue = DEFAULT_UNKNOWN_VALUE) {
    if (value === null || value === undefined) return unknownValue;
    if (typeof value === "number" && !Number.isFinite(value)) return unknownValue;
    if (typeof value === "string") {
        const normalized = value.trim();
        return !normalized || normalized === unknownValue ? unknownValue : normalized;
    }
    return value;
}

export function featureIdentity(feature, fallbackIndex = 0) {
    const properties = feature?.properties || {};
    const sourceLayer = feature?.sourceLayer
        || feature?.layer?.["source-layer"]
        || feature?.layer?.id
        || feature?.source
        || "unknown-layer";
    const element = properties.element || properties.osm_type || "unknown-element";
    const identity = feature?.id ?? properties.id ?? properties.osm_id;
    const safeIdentity = identity === null || identity === undefined || identity === ""
        ? `anonymous-${fallbackIndex}`
        : String(identity);
    return `${sourceLayer}:${element}:${safeIdentity}`;
}

export function deduplicateFeatures(features = []) {
    const unique = new Map();
    features.forEach((feature, index) => {
        const key = featureIdentity(feature, index);
        if (!unique.has(key)) unique.set(key, feature);
    });
    return [...unique.values()];
}

function rounded(value, digits = 6) {
    const power = 10 ** digits;
    return Math.round((value + Number.EPSILON) * power) / power;
}

function diversity(counts) {
    const total = [...counts.values()].reduce((sum, count) => sum + count, 0);
    if (!total) return { shannonEntropy: 0, effectiveDiversity: 0 };
    let shannonEntropy = 0;
    counts.forEach((count) => {
        if (!count) return;
        const probability = count / total;
        shannonEntropy -= probability * Math.log(probability);
    });
    return {
        shannonEntropy: rounded(shannonEntropy),
        effectiveDiversity: rounded(Math.exp(shannonEntropy)),
    };
}

export function summarizeCategoricalValues(values = [], options = {}) {
    const unknownValue = options.unknownValue || DEFAULT_UNKNOWN_VALUE;
    const colors = options.colors || {};
    const otherColor = options.otherColor || "#777777";
    const normalized = values.map((value) => normalizeUnknown(value, unknownValue));
    const knownCounts = new Map();
    let unknown = 0;

    normalized.forEach((value) => {
        if (value === unknownValue) {
            unknown += 1;
            return;
        }
        const key = String(value);
        knownCounts.set(key, (knownCounts.get(key) || 0) + 1);
    });

    const known = normalized.length - unknown;
    const categories = [...knownCounts.entries()]
        .sort(([leftValue, leftCount], [rightValue, rightCount]) => (
            rightCount - leftCount || leftValue.localeCompare(rightValue)
        ))
        .map(([value, count]) => ({
            value,
            count,
            percent: known ? rounded((count / known) * 100, 2) : 0,
            color: colors[value] || otherColor,
        }));
    const metrics = diversity(knownCounts);

    return {
        kind: "categorical",
        total: normalized.length,
        known,
        unknown,
        unknownPercent: normalized.length ? rounded((unknown / normalized.length) * 100, 2) : 0,
        knownCategoryCount: categories.length,
        categories,
        dominant: categories[0] || null,
        ...metrics,
    };
}

function isInvalid(value, invalid) {
    if (!invalid) return false;
    const threshold = Number(invalid.threshold || 0);
    if (invalid.operator === "<=") return value <= threshold;
    if (invalid.operator === ">") return value > threshold;
    if (invalid.operator === ">=") return value >= threshold;
    return value < threshold;
}

function median(values) {
    if (!values.length) return null;
    const sorted = [...values].sort((left, right) => left - right);
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2
        ? sorted[middle]
        : (sorted[middle - 1] + sorted[middle]) / 2;
}

export function summarizeNumericValues(values = [], options = {}) {
    const unknownValue = options.unknownValue || DEFAULT_UNKNOWN_VALUE;
    const breaks = (options.breaks || []).map(Number);
    const colors = options.colors || [];
    const valid = [];
    let unknown = 0;
    let invalid = 0;

    values.forEach((rawValue) => {
        const value = normalizeUnknown(rawValue, unknownValue);
        if (value === unknownValue) {
            unknown += 1;
            return;
        }
        const number = Number(value);
        if (!Number.isFinite(number)) {
            unknown += 1;
        } else if (isInvalid(number, options.invalid)) {
            invalid += 1;
        } else {
            valid.push(number);
        }
    });

    const counts = breaks.map(() => 0);
    valid.forEach((value) => {
        let binIndex = 0;
        breaks.forEach((lowerBound, candidateIndex) => {
            if (value >= lowerBound) binIndex = candidateIndex;
        });
        if (counts.length) counts[binIndex] += 1;
    });

    const bins = breaks.map((lower, index) => {
        const upper = index + 1 < breaks.length ? breaks[index + 1] : null;
        return {
            label: upper === null ? `${lower}+` : `${lower}–<${upper}`,
            lower,
            upper,
            count: counts[index],
            color: colors[index] || "#777777",
        };
    });
    const sum = valid.reduce((total, value) => total + value, 0);

    return {
        kind: "numeric",
        total: values.length,
        known: valid.length,
        unknown,
        unknownPercent: values.length ? rounded((unknown / values.length) * 100, 2) : 0,
        invalid,
        min: valid.length ? Math.min(...valid) : null,
        max: valid.length ? Math.max(...valid) : null,
        mean: valid.length ? rounded(sum / valid.length) : null,
        median: valid.length ? rounded(median(valid)) : null,
        bins,
    };
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

function valueFromFeature(feature, theme) {
    if (theme.attribute === "__layer__") {
        return feature.sourceLayer || feature.layer?.id || DEFAULT_UNKNOWN_VALUE;
    }
    return feature.properties?.[theme.attribute];
}

function collectSingleTheme(map, theme) {
    const layers = visibleAnalyticalLayers(map, theme.layers);
    const rendered = layers.length ? map.queryRenderedFeatures({ layers }) : [];
    const unique = deduplicateFeatures(rendered);
    const values = unique.map((feature) => valueFromFeature(feature, theme));
    const options = {
        unknownValue: theme.unknown_value,
        colors: theme.colors,
        otherColor: theme.other_color,
        breaks: theme.breaks,
        invalid: theme.invalid,
    };
    const summary = theme.kind === "numeric"
        ? summarizeNumericValues(values, options)
        : summarizeCategoricalValues(values, options);
    return {
        ...summary,
        id: theme.id,
        label: theme.label,
        layers,
        source: "visible unique OSM elements",
    };
}

export function collectViewportStats(map, theme) {
    if (theme.kind === "multi") {
        return {
            id: theme.id,
            kind: "multi",
            label: theme.label,
            panels: (theme.panels || []).map((panel) => collectSingleTheme(map, panel)),
            source: "visible unique OSM elements",
        };
    }
    return collectSingleTheme(map, theme);
}

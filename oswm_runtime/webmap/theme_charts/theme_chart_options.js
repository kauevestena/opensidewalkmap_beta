const UNKNOWN_LABEL = "Unknown / missing";
const INVALID_LABEL = "Invalid / not applicable";

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function finite(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
}

export function formatChartNumber(value, maximumFractionDigits = 1) {
    return new Intl.NumberFormat(undefined, {
        maximumFractionDigits,
    }).format(finite(value));
}

function collapseKnownRows(rows, maximum) {
    if (rows.length <= maximum) return rows;
    const visible = rows.slice(0, maximum);
    const tail = rows.slice(maximum);
    visible.push({
        label: `Other known (${tail.length})`,
        value: tail.reduce((total, row) => total + row.value, 0),
        color: "#9aa5aa",
        collapsed: true,
    });
    return visible;
}

function categoricalRows(summary, theme, options = {}) {
    const maximumKnownRows = options.maximumKnownRows || 8;
    const useLength = theme.measure === "length"
        && Number.isFinite(summary.totalLengthKm);
    const total = useLength ? finite(summary.totalLengthKm) : finite(summary.total);
    const rows = (summary.categories || []).map((category) => ({
        label: String(category.value),
        value: useLength
            ? finite(summary.lengthKmByCategory?.[category.value])
            : finite(category.count),
        color: category.color || theme.other_color || "#777777",
        dataValue: true,
    }));
    rows.sort((left, right) => right.value - left.value || left.label.localeCompare(right.label));
    const visible = collapseKnownRows(rows, maximumKnownRows);
    const unknown = useLength
        ? finite(summary.unknownLengthKm)
        : finite(summary.unknown);
    if (unknown > 0) {
        visible.push({
            label: UNKNOWN_LABEL,
            value: unknown,
            color: theme.unknown_color || "#636363",
            unknown: true,
        });
    }
    return visible.map((row) => ({
        ...row,
        percent: total ? (row.value / total) * 100 : 0,
        unit: useLength ? "km" : "features",
    }));
}

function numericRows(summary, theme) {
    const total = finite(summary.total);
    const rows = (summary.bins || []).map((bin) => ({
        label: String(bin.label),
        value: finite(bin.count),
        color: bin.color || "#777777",
        unit: "features",
        dataValue: true,
    }));
    if (finite(summary.invalid) > 0) {
        rows.push({
            label: INVALID_LABEL,
            value: finite(summary.invalid),
            color: theme.invalid?.color || "#808080",
            unit: "features",
            invalid: true,
        });
    }
    if (finite(summary.unknown) > 0) {
        rows.push({
            label: UNKNOWN_LABEL,
            value: finite(summary.unknown),
            color: theme.unknown_color || "#636363",
            unit: "features",
            unknown: true,
        });
    }
    return rows.map((row) => ({
        ...row,
        percent: total ? (row.value / total) * 100 : 0,
    }));
}

export function themeChartRows(summary, theme, options = {}) {
    return summary.kind === "numeric"
        ? numericRows(summary, theme)
        : categoricalRows(summary, theme, options);
}

export function themeMetricSummary(summary, theme) {
    const useLength = theme.measure === "length"
        && Number.isFinite(summary.totalLengthKm);
    if (useLength) {
        return {
            value: finite(summary.totalLengthKm),
            unit: "km",
            label: `${formatChartNumber(summary.totalLengthKm, 2)} km represented`,
        };
    }
    return {
        value: finite(summary.total),
        unit: "features",
        label: `${formatChartNumber(summary.total, 0)} features represented`,
    };
}

function tooltipFormatter(parameters) {
    const item = Array.isArray(parameters) ? parameters[0] : parameters;
    const row = item?.data?.row;
    if (!row) return "";
    const digits = row.unit === "km" ? 2 : 0;
    return `<strong>${escapeHtml(row.label)}</strong><br>`
        + `${escapeHtml(formatChartNumber(row.value, digits))} ${escapeHtml(row.unit)}`
        + ` · ${escapeHtml(formatChartNumber(row.percent, 1))}%`;
}

export function buildThemeChartOption(summary, theme, options = {}) {
    const rows = themeChartRows(summary, theme, options);
    const numeric = summary.kind === "numeric";
    const metric = themeMetricSummary(summary, theme);
    const animationDuration = options.reducedMotion ? 0 : 240;
    const series = {
        type: "bar",
        name: theme.label,
        data: rows.map((row) => ({
            value: row.value,
            row,
            itemStyle: {
                color: row.color,
                borderColor: "rgba(23, 33, 38, .3)",
                borderWidth: 0.5,
            },
        })),
        barMaxWidth: numeric ? 34 : 24,
        emphasis: { focus: "self" },
        animationDuration,
        animationDurationUpdate: animationDuration,
    };
    const categoryAxis = {
        type: "category",
        data: rows.map((row) => row.label),
        axisTick: { show: false },
        axisLabel: {
            color: "#26353c",
            fontSize: 11,
            interval: 0,
            hideOverlap: false,
            overflow: "truncate",
            width: numeric ? 70 : 132,
            rotate: numeric && rows.length > 6 ? 25 : 0,
        },
        inverse: !numeric,
    };
    const valueAxis = {
        type: "value",
        minInterval: metric.unit === "features" ? 1 : undefined,
        name: metric.unit === "km" ? "Kilometres" : "Features",
        nameTextStyle: { color: "#53656d", fontSize: 10 },
        axisLabel: { color: "#53656d", fontSize: 10 },
        splitLine: { lineStyle: { color: "#e1e7e9" } },
    };

    return {
        animationDuration,
        animationDurationUpdate: animationDuration,
        aria: {
            enabled: true,
            description: `${theme.label}. ${metric.label}.`,
        },
        grid: numeric
            ? { left: 44, right: 14, top: 18, bottom: rows.length > 6 ? 58 : 38 }
            : { left: 142, right: 18, top: 12, bottom: 34 },
        tooltip: {
            trigger: "axis",
            axisPointer: { type: "shadow" },
            confine: true,
            formatter: tooltipFormatter,
        },
        xAxis: numeric ? categoryAxis : valueAxis,
        yAxis: numeric ? valueAxis : categoryAxis,
        series: [series],
    };
}

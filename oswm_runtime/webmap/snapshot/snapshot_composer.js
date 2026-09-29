import { collectViewportStats } from "./snapshot_stats.js";
import { renderSummaryChart } from "./snapshot_charts.js";
import { createI18n, DEFAULT_LOCALE, SUPPORTED_LOCALES } from "./snapshot_i18n.js";
import { qrcodeSvg } from "./snapshot_qrcode.js";
import { brandingAssetUrl } from "../../assets/branding/branding.js";

const EXPORT_WIDTH = 1500;
const EXPORT_HEIGHT = 930;
const EXPORT_TIMEOUT_MS = 25000;

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

export function normalizeAuthorPanel(title, content, fontSize = "9px") {
    const normalizedTitle = String(title ?? "").trim();
    const normalizedContent = String(content ?? "").trim();
    let normalizedSize = "9px";
    if (typeof fontSize === "number" || (typeof fontSize === "string" && !isNaN(parseFloat(fontSize)))) {
        const parsed = parseFloat(fontSize);
        const clamped = Math.min(Math.max(parsed, 4), 60);
        normalizedSize = `${Number(clamped.toFixed(1))}px`;
    } else {
        const keywordMap = {
            small: "8px",
            normal: "9px",
            medium: "10.5px",
            large: "12px",
            xlarge: "14px",
        };
        if (keywordMap[fontSize]) {
            normalizedSize = keywordMap[fontSize];
        } else if (typeof fontSize === "string" && /^\d+(\.\d+)?(px|pt|em|rem|%)?$/i.test(fontSize.trim())) {
            normalizedSize = fontSize.trim();
        }
    }

    const contentPx = parseFloat(normalizedSize);
    let titleSize = "14px";
    if (!isNaN(contentPx)) {
        const requiredTitlePx = Math.max(14, contentPx / 0.9);
        titleSize = `${Number(requiredTitlePx.toFixed(1))}px`;
    }

    return {
        title: normalizedTitle,
        content: normalizedContent,
        fontSize: normalizedSize,
        titleFontSize: titleSize,
        visible: Boolean(normalizedTitle || normalizedContent),
    };
}

function sanitizeStyleAttribute(styleValue) {
    if (!styleValue) return "";
    if (/url\s*\(|expression\s*\(|javascript\s*:|-moz-binding/i.test(styleValue)) {
        return "";
    }
    return styleValue;
}

function sanitizeAuthorContent(content) {
    if (!content) return "";
    if (!/<\/?[a-z][\s\S]*>/i.test(content)) {
        return `<p>${escapeHtml(content).replaceAll("\n", "<br>")}</p>`;
    }

    const allowedTags = new Set([
        "A", "B", "BR", "CODE", "EM", "I", "LI", "OL", "P", "SMALL",
        "SPAN", "STRONG", "SUB", "SUP", "U", "UL",
    ]);
    const removedTags = new Set(["EMBED", "IFRAME", "OBJECT", "SCRIPT", "STYLE"]);
    const template = document.createElement("template");
    template.innerHTML = content;

    [...template.content.querySelectorAll("*")].forEach((element) => {
        if (removedTags.has(element.tagName)) {
            element.remove();
            return;
        }
        if (!allowedTags.has(element.tagName)) {
            element.replaceWith(...element.childNodes);
            return;
        }

        [...element.attributes].forEach((attribute) => {
            const isAllowedAnchorAttr = element.tagName === "A"
                && (attribute.name === "href" || attribute.name === "title");
            const isStyleAttr = attribute.name === "style";
            const isSafeAttr = attribute.name === "dir" || attribute.name === "class";

            if (isStyleAttr) {
                const cleanStyle = sanitizeStyleAttribute(attribute.value);
                if (cleanStyle) {
                    element.setAttribute("style", cleanStyle);
                } else {
                    element.removeAttribute("style");
                }
            } else if (!isAllowedAnchorAttr && !isSafeAttr) {
                element.removeAttribute(attribute.name);
            }
        });
        if (element.tagName === "A") {
            const href = element.getAttribute("href") || "";
            if (!/^(https?:|mailto:|#)/i.test(href)) element.removeAttribute("href");
            element.setAttribute("rel", "noopener noreferrer");
        }
    });
    return template.innerHTML;
}

function authorPanelMarkup(title, content, fontSize = "9px") {
    const panel = normalizeAuthorPanel(title, content, fontSize);
    if (!panel.visible) return "";
    const titleStyle = panel.titleFontSize ? ` style="font-size:${escapeHtml(panel.titleFontSize)};"` : "";
    return `<section class="oswm-snapshot-analysis-block oswm-snapshot-author-panel">
        ${panel.title ? `<h2 dir="auto"${titleStyle}>${escapeHtml(panel.title)}</h2>` : ""}
        ${panel.content ? `<div class="oswm-snapshot-author-content" dir="auto" style="font-size:${escapeHtml(panel.fontSize)};">${sanitizeAuthorContent(panel.content)}</div>` : ""}
    </section>`;
}

function formatNumber(value, digits = 1) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(Number(value));
}

export function normalizeBounds(bounds) {
    if (!bounds) throw new Error("Snapshot extent is unavailable.");
    if (typeof bounds.getWest === "function") {
        return [[bounds.getWest(), bounds.getSouth()], [bounds.getEast(), bounds.getNorth()]];
    }
    if (Array.isArray(bounds) && bounds.length === 4) {
        return [[Number(bounds[0]), Number(bounds[1])], [Number(bounds[2]), Number(bounds[3])]];
    }
    if (Array.isArray(bounds) && bounds.length === 2 && bounds.every(Array.isArray)) {
        return bounds.map((corner) => corner.map(Number));
    }
    throw new Error("Snapshot extent has an unsupported format.");
}

export function stripRasterBasemap(style) {
    const vectorStyle = JSON.parse(JSON.stringify(style));
    const rasterSources = new Set(
        Object.entries(vectorStyle.sources || {})
            .filter(([, source]) => source.type === "raster" || source.type === "raster-dem")
            .map(([sourceId]) => sourceId),
    );
    vectorStyle.layers = (vectorStyle.layers || []).filter(
        (layer) => layer.type !== "raster" && !rasterSources.has(layer.source),
    );
    rasterSources.forEach((sourceId) => delete vectorStyle.sources[sourceId]);
    delete vectorStyle.terrain;
    return vectorStyle;
}

export function computeScaleBar(latitude, zoom, targetPixels = 120) {
    const earthCircumference = 40075016.686;
    const metersPerPixel = (
        earthCircumference * Math.cos((Number(latitude) * Math.PI) / 180)
    ) / (512 * (2 ** Number(zoom)));
    const rawDistance = Math.max(metersPerPixel * targetPixels, 0.001);
    const magnitude = 10 ** Math.floor(Math.log10(rawDistance));
    const normalized = rawDistance / magnitude;
    const niceFactor = normalized >= 5 ? 5 : normalized >= 2 ? 2 : 1;
    const meters = niceFactor * magnitude;
    return {
        meters,
        widthPixels: meters / metersPerPixel,
        label: meters >= 1000
            ? `${formatNumber(meters / 1000, 2)} km`
            : `${formatNumber(meters, 0)} m`,
    };
}

function waitForIdle(map, timeoutMs = EXPORT_TIMEOUT_MS) {
    return new Promise((resolve, reject) => {
        let settled = false;
        const finish = (callback, value) => {
            if (settled) return;
            settled = true;
            clearTimeout(timer);
            callback(value);
        };
        const timer = setTimeout(
            () => finish(reject, new Error("Timed out while waiting for map tiles.")),
            timeoutMs,
        );
        map.once("idle", () => finish(resolve));
        try {
            if (map.isStyleLoaded?.() && map.areTilesLoaded?.()) finish(resolve);
        } catch (_error) {
            // The idle listener remains authoritative while the style initializes.
        }
    });
}

async function nextFrame() {
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

async function renderExportMap(maplibregl, style, bounds) {
    const container = document.createElement("div");
    container.className = "oswm-snapshot-export-map";
    container.style.width = `${EXPORT_WIDTH}px`;
    container.style.height = `${EXPORT_HEIGHT}px`;
    document.body.appendChild(container);
    let exportMap;
    try {
        exportMap = new maplibregl.Map({
            container,
            style,
            bounds,
            fitBoundsOptions: { padding: 24, duration: 0 },
            bearing: 0,
            pitch: 0,
            interactive: false,
            attributionControl: false,
            pixelRatio: 2,
            canvasContextAttributes: {
                antialias: true,
                preserveDrawingBuffer: true,
            },
            fadeDuration: 0,
        });
        await waitForIdle(exportMap);
        exportMap.resize();
        await nextFrame();
        const canvas = exportMap.getCanvas();
        if (!canvas.width || !canvas.height) throw new Error("The export map canvas is empty.");
        const imageUrl = canvas.toDataURL("image/png");
        if (!imageUrl || imageUrl.length < 1000) throw new Error("The export map image is blank.");
        return {
            imageUrl,
            scale: computeScaleBar(exportMap.getCenter().lat, exportMap.getZoom()),
        };
    } finally {
        if (exportMap) exportMap.remove();
        container.remove();
    }
}

async function captureMap(map, bounds, maplibregl) {
    if (!maplibregl?.Map) {
        throw new Error("The MapLibre renderer was not supplied to the snapshot composer.");
    }
    const style = JSON.parse(JSON.stringify(map.getStyle()));
    try {
        return await renderExportMap(maplibregl, style, bounds);
    } catch (primaryError) {
        try {
            const fallback = await renderExportMap(
                maplibregl,
                stripRasterBasemap(style),
                bounds,
            );
            return {
                ...fallback,
                warningCode: "basemapFallback",
            };
        } catch (fallbackError) {
            throw new Error(
                `Map rendering failed (${primaryError.message}; fallback: ${fallbackError.message}).`,
            );
        }
    }
}

function localizedThemeLabel(theme, i18n) {
    return i18n.themeLabel(theme.id, theme.label);
}

export function formatScaleLabel(scale, i18n = createI18n()) {
    return scale.meters >= 1000
        ? `${i18n.formatNumber(scale.meters / 1000, 2)} ${i18n.t("unitKm")}`
        : `${i18n.formatNumber(scale.meters, 0)} ${i18n.t("unitM")}`;
}

function categoricalFacts(summary, i18n) {
    const dominant = summary.dominant
        ? `<bdi dir="ltr">${escapeHtml(summary.dominant.value)}</bdi> (${i18n.formatPercent(summary.dominant.percent)} ${escapeHtml(i18n.t("ofKnown"))})`
        : "—";
    const lengthFacts = summary.totalLengthKm === undefined ? "" : `
            <div><dt>${escapeHtml(i18n.t("mappedLineLength"))}</dt><dd>${i18n.formatNumber(summary.totalLengthKm, 2)} ${escapeHtml(i18n.t("unitKm"))}</dd></div>
            <div><dt>${escapeHtml(i18n.t("lengthWithoutValue"))}</dt><dd>${i18n.formatNumber(summary.unknownLengthKm, 2)} ${escapeHtml(i18n.t("unitKm"))}</dd></div>`;
    return `
        <dl class="oswm-snapshot-facts">
            <div><dt>${escapeHtml(i18n.t("uniqueElements"))}</dt><dd>${i18n.formatNumber(summary.total, 0)}</dd></div>
            <div><dt>${escapeHtml(i18n.t("knownValues"))}</dt><dd>${i18n.formatNumber(summary.known, 0)}</dd></div>
            <div><dt>${escapeHtml(i18n.t("unknownMissing"))}</dt><dd>${i18n.formatNumber(summary.unknown, 0)} (${i18n.formatPercent(summary.unknownPercent)})</dd></div>
            <div><dt>${escapeHtml(i18n.t("knownCategories"))}</dt><dd>${i18n.formatNumber(summary.knownCategoryCount, 0)}</dd></div>
            <div><dt>${escapeHtml(i18n.t("dominantCategory"))}</dt><dd>${dominant}</dd></div>
            <div><dt>${escapeHtml(i18n.t("shannonEntropy"))}</dt><dd>${i18n.formatNumber(summary.shannonEntropy, 3)}</dd></div>
            <div><dt>${escapeHtml(i18n.t("effectiveDiversity"))}</dt><dd>${i18n.formatNumber(summary.effectiveDiversity, 2)}</dd></div>
            ${lengthFacts}
        </dl>`;
}

function numericFacts(summary, i18n) {
    return `
        <dl class="oswm-snapshot-facts">
            <div><dt>${escapeHtml(i18n.t("uniqueElements"))}</dt><dd>${i18n.formatNumber(summary.total, 0)}</dd></div>
            <div><dt>${escapeHtml(i18n.t("validValues"))}</dt><dd>${i18n.formatNumber(summary.known, 0)}</dd></div>
            <div><dt>${escapeHtml(i18n.t("unknownMissing"))}</dt><dd>${i18n.formatNumber(summary.unknown, 0)} (${i18n.formatPercent(summary.unknownPercent)})</dd></div>
            <div><dt>${escapeHtml(i18n.t("invalidNa"))}</dt><dd>${i18n.formatNumber(summary.invalid, 0)}</dd></div>
            <div><dt>${escapeHtml(i18n.t("median"))}</dt><dd>${i18n.formatNumber(summary.median, 2)}</dd></div>
            <div><dt>${escapeHtml(i18n.t("range"))}</dt><dd>${i18n.formatNumber(summary.min, 2)} – ${i18n.formatNumber(summary.max, 2)}</dd></div>
        </dl>`;
}

function renderFacts(summary, i18n) {
    if (summary.kind === "multi") {
        return summary.panels.map((panel) => `
            <section class="oswm-snapshot-fact-panel">
                <h3>${escapeHtml(localizedThemeLabel(panel, i18n))}</h3>
                ${panel.kind === "numeric" ? numericFacts(panel, i18n) : categoricalFacts(panel, i18n)}
            </section>`).join("");
    }
    return summary.kind === "numeric"
        ? numericFacts(summary, i18n)
        : categoricalFacts(summary, i18n);
}

function chartOptions(i18n) {
    return {
        width: 560,
        rowHeight: 28,
        showTitle: false,
        locale: i18n.locale,
        direction: i18n.direction,
        otherKnownLabel: (count) => i18n.t("otherKnown", {
            count: i18n.formatNumber(count, 0),
        }),
        unknownLabel: i18n.t("unknownMissing"),
        invalidLabel: i18n.t("invalidNa"),
        ofKnownLabel: i18n.t("ofKnown"),
        ofAllLabel: i18n.t("ofAll"),
        noFeaturesLabel: i18n.t("noFeatures"),
        formatNumber: (value, digits) => i18n.formatNumber(value, digits),
        formatPercent: (value, digits) => i18n.formatPercent(value, digits),
    };
}

function renderCharts(summary, theme, i18n) {
    const options = chartOptions(i18n);
    if (summary.kind === "multi") {
        return summary.panels.map((panel, index) => {
            const panelTheme = theme.panels[index] || panel;
            const label = localizedThemeLabel(panelTheme, i18n);
            return `
                <section class="oswm-snapshot-chart-subpanel">
                    <h3>${escapeHtml(label)}</h3>
                    ${renderSummaryChart(panel, { ...panelTheme, label }, options)}
                </section>`;
        }).join("");
    }
    return renderSummaryChart(
        summary,
        { ...theme, label: localizedThemeLabel(theme, i18n) },
        options,
    );
}

function legendEntries(summary, theme, i18n) {
    if (summary.kind === "numeric") {
        const entries = (summary.bins || []).map((bin) => ({
            label: bin.label,
            color: bin.color,
            dataValue: true,
        }));
        if (summary.invalid) entries.push({
            label: i18n.t("invalidNa"),
            color: theme.invalid?.color || "#808080",
        });
        if (summary.unknown) entries.push({
            label: i18n.t("unknownMissing"),
            color: theme.unknown_color || "#636363",
        });
        return entries;
    }
    const entries = (summary.categories || []).slice(0, 12).map((category) => ({
        label: category.value,
        color: category.color,
        dataValue: true,
    }));
    if (summary.unknown) entries.push({
        label: i18n.t("unknownMissing"),
        color: theme.unknown_color || "#636363",
    });
    return entries;
}

function renderLegendBlock(summary, theme, i18n) {
    const entries = legendEntries(summary, theme, i18n);
    return `<section class="oswm-snapshot-legend-block">
        <h3>${escapeHtml(localizedThemeLabel(theme, i18n))}</h3>
        <div class="oswm-snapshot-legend-items">
            ${entries.map((entry) => `<span><i style="--legend-color:${escapeHtml(entry.color)}"></i>${entry.dataValue ? `<bdi dir="ltr">${escapeHtml(entry.label)}</bdi>` : escapeHtml(entry.label)}</span>`).join("")}
            ${entries.length ? "" : `<em>${escapeHtml(i18n.t("noClassified"))}</em>`}
        </div>
    </section>`;
}

function renderLegend(summary, theme, i18n) {
    if (summary.kind === "multi") {
        return summary.panels.map((panel, index) => (
            renderLegendBlock(panel, theme.panels[index] || panel, i18n)
        )).join("");
    }
    return renderLegendBlock(summary, theme, i18n);
}

function boundsText(bounds, i18n) {
    const [[west, south], [east, north]] = bounds;
    return `${i18n.t("westShort")} ${west.toFixed(5)} · ${i18n.t("southShort")} ${south.toFixed(5)} · ${i18n.t("eastShort")} ${east.toFixed(5)} · ${i18n.t("northShort")} ${north.toFixed(5)}`;
}

export function renderSnapshotSheet({
    title,
    nodeName,
    theme,
    summary,
    scope,
    bounds,
    capture,
    generatedAt,
    authorTitle,
    authorContent,
    authorFontSize,
    i18n,
    logoDataUrl,
    webmapUrl,
}) {
    const scopeLabel = i18n.t(scope === "node" ? "wholeNode" : "currentViewport");
    const timestamp = i18n.formatDate(generatedAt || new Date());
    const sourceNote = i18n.t(scope === "node" ? "exactNodeSource" : "viewportSource");
    const themeLabel = localizedThemeLabel(theme, i18n);
    const warning = capture.warningCode ? i18n.t(capture.warningCode) : "";
    const logoMarkup = logoDataUrl
        ? `<img src="${logoDataUrl}" alt="OpenSidewalkMap" class="oswm-snapshot-header-logo">`
        : "";
    const qrMarkup = webmapUrl
        ? `<div class="oswm-snapshot-qr" title="${escapeHtml(i18n.t("qrCodeAlt"))}">${qrcodeSvg(webmapUrl, { size: 72 })}</div>`
        : "";
    return `<article class="oswm-snapshot-print-sheet" lang="${escapeHtml(i18n.locale)}" dir="${escapeHtml(i18n.direction)}">
        <header class="oswm-snapshot-sheet-header">
            ${logoMarkup}
            <div>
                <p class="oswm-snapshot-kicker">${escapeHtml(i18n.t("scrutinyMapKicker"))}</p>
                <h1 dir="auto">${escapeHtml(title)}</h1>
            </div>
            <dl>
                <div><dt>${escapeHtml(i18n.t("node"))}</dt><dd dir="auto">${escapeHtml(nodeName)}</dd></div>
                <div><dt>${escapeHtml(i18n.t("theme"))}</dt><dd>${escapeHtml(themeLabel)}</dd></div>
                <div><dt>${escapeHtml(i18n.t("scope"))}</dt><dd>${escapeHtml(scopeLabel)}</dd></div>
                <div><dt>${escapeHtml(i18n.t("generated"))}</dt><dd>${escapeHtml(timestamp)}</dd></div>
            </dl>
        </header>
        <div class="oswm-snapshot-sheet-grid">
            <section class="oswm-snapshot-map-column">
                <div class="oswm-snapshot-map-frame">
                    <img src="${capture.imageUrl}" alt="${escapeHtml(i18n.t("mapAlt"))}" class="oswm-snapshot-map-image">
                    ${qrMarkup}
                    <div class="oswm-snapshot-north" aria-label="${escapeHtml(i18n.t("northLabel"))}"><span>▲</span>${escapeHtml(i18n.t("north"))}</div>
                    <div class="oswm-snapshot-scale" style="--scale-width:${capture.scale.widthPixels}px">
                        <span></span><b>${escapeHtml(formatScaleLabel(capture.scale, i18n))}</b>
                    </div>
                </div>
                <p class="oswm-snapshot-extent">${escapeHtml(boundsText(bounds, i18n))}</p>
                ${warning ? `<p class="oswm-snapshot-warning">${escapeHtml(warning)}</p>` : ""}
            </section>
            <aside class="oswm-snapshot-analysis-column">
                <section class="oswm-snapshot-analysis-block">
                    <h2>${escapeHtml(i18n.t("scrutinyFacts"))}</h2>
                    ${renderFacts(summary, i18n)}
                </section>
                <section class="oswm-snapshot-analysis-block oswm-snapshot-chart-block">
                    <h2>${escapeHtml(i18n.t("theme"))}</h2>
                    <p class="oswm-snapshot-theme-name">${escapeHtml(themeLabel)}</p>
                    ${renderCharts(summary, theme, i18n)}
                </section>
                <section class="oswm-snapshot-analysis-block oswm-snapshot-legend">
                    <h2>${escapeHtml(i18n.t("legend"))}</h2>
                    ${renderLegend(summary, theme, i18n)}
                </section>
                <div class="oswm-snapshot-author-slot">
                    ${authorPanelMarkup(authorTitle, authorContent, authorFontSize)}
                </div>
            </aside>
        </div>
        <footer>
            <span>${escapeHtml(sourceNote)}</span>
            <span>${escapeHtml(i18n.t("attribution"))}</span>
        </footer>
    </article>`;
}

export class SnapshotComposer {
    constructor(map, params, options = {}) {
        this.map = map;
        this.params = params;
        this.getActiveStyleKey = options.getActiveStyleKey || (() => "footway_categories");
        this.maplibregl = options.maplibregl || globalThis.maplibregl;
        this.root = null;
        this.summaryCache = null;
        this.logoDataUrl = null;
        this.i18n = createI18n(DEFAULT_LOCALE);
        this.lastRenderContext = null;
        this.statusKey = null;
        this.renderToken = 0;
        this.keyHandler = (event) => {
            if (event.key === "Escape") this.close();
        };
    }

    /** Preload the project banner as a data-URL so it renders in print/PDF. */
    async preloadLogo() {
        if (this.logoDataUrl) return;
        try {
            const response = await fetch(await brandingAssetUrl("logos.page_clean"));
            if (!response.ok) return;
            const blob = await response.blob();
            this.logoDataUrl = await new Promise((resolve) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            });
        } catch (_error) {
            // Logo is optional — silently degrade if fetch fails.
        }
    }

    /** Build the full webmap URL including the current MapLibre hash. */
    webmapUrl() {
        const base = this.params.node_url || "";
        // The webmap is always at map.html relative to the node root.
        const mapPage = base.endsWith("/") ? `${base}map.html` : `${base}/map.html`;
        // Capture the current hash from the live browser URL if it has the
        // MapLibre pattern (#map=zoom/lat/lng), otherwise just use the page URL.
        const hash = window.location.hash;
        if (/^#map=/.test(hash)) return mapPage + hash;
        // Fallback: construct from current map state.
        try {
            const center = this.map.getCenter();
            const zoom = Math.round(this.map.getZoom() * 10) / 10;
            return `${mapPage}#map=${zoom}/${center.lat.toFixed(5)}/${center.lng.toFixed(5)}`;
        } catch (_error) {
            return mapPage;
        }
    }

    build() {
        if (this.root) return;
        const localeOptions = SUPPORTED_LOCALES.map((locale) => (
            `<option value="${escapeHtml(locale.code)}" lang="${escapeHtml(locale.code)}" dir="${escapeHtml(locale.direction)}">${escapeHtml(locale.label)}</option>`
        )).join("");
        this.root = document.createElement("div");
        this.root.className = "oswm-snapshot-backdrop is-hidden";
        this.root.setAttribute("role", "dialog");
        this.root.setAttribute("aria-modal", "true");
        this.root.setAttribute("aria-labelledby", "oswm-snapshot-dialog-title");
        this.root.innerHTML = `
            <section class="oswm-snapshot-modal">
                <header class="oswm-snapshot-modal-header">
                    <div>
                        <p data-i18n="printableSnapshot">Printable Webmap snapshot</p>
                        <h2 id="oswm-snapshot-dialog-title" data-i18n="createScrutinyMap">Create scrutiny map</h2>
                    </div>
                    <button type="button" class="oswm-snapshot-close" aria-label="Close snapshot composer" data-i18n-aria-label="closeComposer">×</button>
                </header>
                <form class="oswm-snapshot-options" onsubmit="return false">
                    <label><span data-i18n="title">Title</span><input name="title" type="text" maxlength="100"></label>
                    <div class="oswm-snapshot-selector-pair">
                        <label><span data-i18n="scope">Scope</span><select name="scope"><option value="viewport" data-i18n="currentViewport">Current viewport</option><option value="node" data-i18n="wholeNode">Whole node</option></select></label>
                        <label><span data-i18n="language">Language</span><select name="locale">${localeOptions}</select></label>
                    </div>
                    <span class="oswm-snapshot-format" data-i18n="formatA4">A4 · Landscape · North-up</span>
                    <button type="button" data-action="update" data-i18n="updatePreview">Update preview</button>
                    <details class="oswm-snapshot-extra-options">
                        <summary data-i18n="optionalAuthorPanel">Optional author panel</summary>
                        <div class="oswm-snapshot-extra-fields">
                            <label><span data-i18n="panelTitle">Panel title</span><input name="author-title" type="text" maxlength="80" placeholder="e.g. Field notes" data-i18n-placeholder="panelTitlePlaceholder"></label>
                            <label><span data-i18n="fontSize">Font size</span>
                                <div class="oswm-snapshot-fontsize-stepper">
                                    <button type="button" class="oswm-fontsize-btn" data-step="-0.5" aria-label="Decrease font size" data-i18n-aria-label="decreaseFontSize">−</button>
                                    <input name="author-font-size" type="number" min="5" max="40" step="0.5" value="9">
                                    <span class="oswm-fontsize-unit">px</span>
                                    <button type="button" class="oswm-fontsize-btn" data-step="+0.5" aria-label="Increase font size" data-i18n-aria-label="increaseFontSize">+</button>
                                </div>
                            </label>
                            <label class="oswm-snapshot-full-width"><span data-i18n="textOrSafeHtml">Text or safe HTML</span><textarea name="author-content" rows="3" maxlength="4000" placeholder="Comments, interpretation or extra facts…" data-i18n-placeholder="authorContentPlaceholder"></textarea></label>
                        </div>
                    </details>
                </form>
                <div class="oswm-snapshot-status" role="status" aria-live="polite"></div>
                <main class="oswm-snapshot-preview"></main>
                <footer class="oswm-snapshot-actions">
                    <button type="button" data-action="cancel" class="secondary" data-i18n="cancel">Cancel</button>
                    <button type="button" data-action="print" data-i18n="printSavePdf" disabled>Print / Save as PDF</button>
                </footer>
            </section>`;
        document.body.appendChild(this.root);
        this.root.querySelector('[name="locale"]').value = this.i18n.locale;
        this.applyTranslations();
        this.root.querySelector(".oswm-snapshot-close").addEventListener("click", () => this.close());
        this.root.querySelector('[data-action="cancel"]').addEventListener("click", () => this.close());
        this.root.querySelector('[data-action="update"]').addEventListener("click", () => this.updatePreview());
        this.root.querySelector('[data-action="print"]').addEventListener("click", () => this.print());
        this.root.querySelector('[name="scope"]').addEventListener("change", () => this.updatePreview());
        this.root.querySelector('[name="locale"]').addEventListener("change", (event) => {
            this.changeLocale(event.target.value);
        });
        this.root.querySelector('[name="title"]').addEventListener("input", (event) => {
            const heading = this.root.querySelector(".oswm-snapshot-print-sheet h1");
            if (heading) heading.textContent = event.target.value || this.defaultTitle();
        });
        const fontSizeInput = this.root.querySelector('[name="author-font-size"]');
        this.root.querySelectorAll(".oswm-fontsize-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const delta = parseFloat(btn.dataset.step) || 0;
                const current = parseFloat(fontSizeInput.value) || 9;
                const updated = Math.min(Math.max(current + delta, 5), 40);
                fontSizeInput.value = Number(updated.toFixed(1));
                this.updateAuthorPanel();
            });
        });
        ["author-title", "author-content", "author-font-size"].forEach((fieldName) => {
            const field = this.root.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.addEventListener("input", () => this.updateAuthorPanel());
                field.addEventListener("change", () => this.updateAuthorPanel());
            }
        });
    }

    applyTranslations() {
        if (!this.root) return;
        this.root.lang = this.i18n.locale;
        this.root.dir = this.i18n.direction;
        this.root.querySelectorAll("[data-i18n]").forEach((element) => {
            element.textContent = this.i18n.t(element.dataset.i18n);
        });
        this.root.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
            element.placeholder = this.i18n.t(element.dataset.i18nPlaceholder);
        });
        this.root.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
            element.setAttribute("aria-label", this.i18n.t(element.dataset.i18nAriaLabel));
        });
        if (this.statusKey) {
            this.root.querySelector(".oswm-snapshot-status").textContent = this.i18n.t(this.statusKey);
        }
    }

    setStatus(key) {
        this.statusKey = key;
        const status = this.root?.querySelector(".oswm-snapshot-status");
        if (status) status.textContent = this.i18n.t(key);
    }

    changeLocale(locale) {
        const previousDefaultTitle = this.defaultTitle();
        const titleInput = this.root.querySelector('[name="title"]');
        const shouldLocalizeTitle = !titleInput.value.trim()
            || titleInput.value === previousDefaultTitle;
        this.i18n = createI18n(locale);
        this.root.querySelector('[name="locale"]').value = this.i18n.locale;
        if (shouldLocalizeTitle) titleInput.value = this.defaultTitle();
        this.applyTranslations();
        this.renderLastSheet();
    }

    activeTheme() {
        const styleKey = this.getActiveStyleKey();
        const configured = this.params.snapshot?.themes?.[styleKey];
        if (configured) return configured;
        return {
            id: styleKey,
            kind: "categorical",
            label: this.params.styles?.[styleKey]?.name || styleKey,
            attribute: "__layer__",
            layers: this.params.data_layers || [],
            colors: {},
            unknown_value: "?",
            unknown_color: "#636363",
        };
    }

    defaultTitle() {
        const theme = this.activeTheme();
        return this.i18n.t("defaultTitle", {
            theme: localizedThemeLabel(theme, this.i18n),
        });
    }

    renderLastSheet() {
        if (!this.lastRenderContext) return false;
        const preview = this.root.querySelector(".oswm-snapshot-preview");
        preview.innerHTML = renderSnapshotSheet({
            ...this.lastRenderContext,
            title: this.root.querySelector('[name="title"]').value || this.defaultTitle(),
            authorTitle: this.root.querySelector('[name="author-title"]').value,
            authorContent: this.root.querySelector('[name="author-content"]').value,
            authorFontSize: this.root.querySelector('[name="author-font-size"]')?.value || "9",
            i18n: this.i18n,
            logoDataUrl: this.logoDataUrl,
            webmapUrl: this.webmapUrl(),
        });
        return true;
    }

    updateAuthorPanel() {
        const slot = this.root?.querySelector(".oswm-snapshot-author-slot");
        if (!slot) return;
        slot.innerHTML = authorPanelMarkup(
            this.root.querySelector('[name="author-title"]').value,
            this.root.querySelector('[name="author-content"]').value,
            this.root.querySelector('[name="author-font-size"]')?.value || "9",
        );
    }

    async open() {
        this.build();
        this.preloadLogo(); // fire-and-forget; logo arrives before print.
        this.root.classList.remove("is-hidden");
        document.body.classList.add("oswm-snapshot-modal-open");
        document.addEventListener("keydown", this.keyHandler);
        const titleInput = this.root.querySelector('[name="title"]');
        titleInput.value = this.defaultTitle();
        this.root.querySelector('[name="scope"]').value = this.params.snapshot?.default_scope || "viewport";
        this.root.querySelector(".oswm-snapshot-close").focus();
        await this.updatePreview();
    }

    close() {
        if (!this.root) return;
        this.renderToken += 1;
        this.root.classList.add("is-hidden");
        document.body.classList.remove("oswm-snapshot-modal-open");
        document.removeEventListener("keydown", this.keyHandler);
    }

    destroy() {
        this.close();
        this.root?.remove();
        this.root = null;
    }

    async nodeSummary(themeId) {
        if (!this.summaryCache) {
            const response = await fetch(this.params.snapshot.summary_url, { cache: "no-store" });
            if (!response.ok) throw new Error(`Node summary is unavailable (HTTP ${response.status}).`);
            this.summaryCache = await response.json();
        }
        const summary = this.summaryCache.themes?.[themeId];
        if (!summary) throw new Error(`No whole-node summary exists for theme “${themeId}”.`);
        return { summary, generatedAt: this.summaryCache.generated_at };
    }

    async updatePreview() {
        if (!this.root || this.root.classList.contains("is-hidden")) return;
        const token = ++this.renderToken;
        const preview = this.root.querySelector(".oswm-snapshot-preview");
        const printButton = this.root.querySelector('[data-action="print"]');
        const updateButton = this.root.querySelector('[data-action="update"]');
        this.lastRenderContext = null;
        printButton.disabled = true;
        updateButton.disabled = true;
        this.setStatus("preparing");
        preview.innerHTML = `<div class="oswm-snapshot-loading" data-i18n="renderingPreview">${escapeHtml(this.i18n.t("renderingPreview"))}</div>`;

        try {
            await waitForIdle(this.map, 15000);
            const theme = this.activeTheme();
            const scope = this.root.querySelector('[name="scope"]').value;
            const bounds = normalizeBounds(scope === "node" ? this.params.bounds : this.map.getBounds());
            let summary;
            let generatedAt;
            if (scope === "node") {
                ({ summary, generatedAt } = await this.nodeSummary(theme.id));
            } else {
                summary = collectViewportStats(this.map, theme);
            }
            const capture = await captureMap(this.map, bounds, this.maplibregl);
            if (token !== this.renderToken) return;
            this.lastRenderContext = {
                nodeName: this.params.snapshot?.node_name || "OSWM node",
                theme,
                summary,
                scope,
                bounds,
                capture,
                generatedAt: generatedAt || new Date().toISOString(),
                logoDataUrl: this.logoDataUrl,
                webmapUrl: this.webmapUrl(),
            };
            this.renderLastSheet();
            this.setStatus(capture.warningCode || "ready");
            printButton.disabled = false;
        } catch (error) {
            if (token !== this.renderToken) return;
            preview.innerHTML = `<div class="oswm-snapshot-error"><strong data-i18n="snapshotCouldNotBePrepared">${escapeHtml(this.i18n.t("snapshotCouldNotBePrepared"))}</strong><p>${escapeHtml(error.message)}</p></div>`;
            this.setStatus("renderingFailed");
        } finally {
            if (token === this.renderToken) updateButton.disabled = false;
        }
    }

    print() {
        if (!this.root?.querySelector(".oswm-snapshot-print-sheet")) return;
        const previousTitle = document.title;
        const requestedTitle = this.root.querySelector('[name="title"]').value || this.defaultTitle();
        const restore = () => {
            document.title = previousTitle;
            document.body.classList.remove("oswm-snapshot-printing");
        };
        document.title = requestedTitle;
        document.body.classList.add("oswm-snapshot-printing");
        window.addEventListener("afterprint", restore, { once: true });
        window.print();
        setTimeout(restore, 1000);
    }
}

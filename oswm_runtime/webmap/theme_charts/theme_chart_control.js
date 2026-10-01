import { collectViewportThemeStats } from "./theme_chart_stats.js";
import {
    buildThemeChartOption,
    formatChartNumber,
    themeChartRows,
    themeMetricSummary,
} from "./theme_chart_options.js";

const PANEL_ID = "oswm-theme-chart-panel";

function createElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
}

function formattedRevision(value) {
    if (!value) return "unknown revision";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date);
}

export class ThemeChartControl {
    constructor(params, options = {}) {
        this.config = params?.theme_charts || params || {};
        this.options = options;
        this.echarts = options.echarts;
        this.echartsPromise = null;
        this.map = null;
        this.container = null;
        this.panel = null;
        this.button = null;
        this.title = null;
        this.status = null;
        this.content = null;
        this.viewportInput = null;
        this.activeStyleKey = null;
        this.summaryPromise = null;
        this.charts = [];
        this.opened = false;
        this.renderSequence = 0;
        this.renderTimer = null;
        this.handleMoveEnd = () => {
            if (this.opened && this.viewportInput?.checked) this.scheduleRender(100);
        };
        this.handleStyleData = () => {
            if (this.opened && this.viewportInput?.checked) this.scheduleRender(180);
        };
        this.handleResize = () => this.charts.forEach((chart) => chart.resize());
    }

    onAdd(map) {
        this.map = map;
        this.container = createElement("div", "maplibregl-ctrl oswm-theme-chart-control");

        this.button = createElement("button", "oswm-theme-chart-toggle");
        this.button.type = "button";
        this.button.title = "Analyze the active map theme";
        this.button.setAttribute("aria-label", "Analyze the active map theme");
        this.button.setAttribute("aria-expanded", "false");
        this.button.setAttribute("aria-controls", PANEL_ID);
        this.button.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M4 20V10h4v10H4Zm6 0V4h4v16h-4Zm6 0v-7h4v7h-4Z"></path>
        </svg>`;
        this.button.addEventListener("click", () => this.toggle());

        this.panel = createElement("section", "oswm-theme-chart-panel is-hidden");
        this.panel.id = PANEL_ID;
        this.panel.setAttribute("aria-label", "Map theme analysis");

        const header = createElement("header", "oswm-theme-chart-header");
        const headingGroup = createElement("div", "oswm-theme-chart-heading");
        const eyebrow = createElement("span", "oswm-theme-chart-eyebrow", "Map analysis");
        this.title = createElement("h2", "oswm-theme-chart-title", "Active theme");
        headingGroup.append(eyebrow, this.title);
        const closeButton = createElement("button", "oswm-theme-chart-close", "×");
        closeButton.type = "button";
        closeButton.title = "Close map analysis";
        closeButton.setAttribute("aria-label", "Close map analysis");
        closeButton.addEventListener("click", () => this.close());
        header.append(headingGroup, closeButton);

        const controls = createElement("div", "oswm-theme-chart-controls");
        const scopeLabel = createElement("label", "oswm-theme-chart-scope");
        this.viewportInput = document.createElement("input");
        this.viewportInput.type = "checkbox";
        this.viewportInput.checked = this.config.default_scope === "viewport";
        this.viewportInput.addEventListener("change", () => this.render());
        scopeLabel.append(
            this.viewportInput,
            createElement("span", "", "Visible area"),
            createElement("small", "", "live estimate"),
        );
        controls.appendChild(scopeLabel);

        this.status = createElement("p", "oswm-theme-chart-status", "Ready");
        this.status.setAttribute("aria-live", "polite");
        this.content = createElement("div", "oswm-theme-chart-content");
        this.panel.append(header, controls, this.status, this.content);
        this.container.append(this.button, this.panel);

        map.on("moveend", this.handleMoveEnd);
        map.on("styledata", this.handleStyleData);
        window.addEventListener("resize", this.handleResize);
        this.setActiveStyle(this.currentStyleKey());
        return this.container;
    }

    onRemove() {
        clearTimeout(this.renderTimer);
        this.map?.off("moveend", this.handleMoveEnd);
        this.map?.off("styledata", this.handleStyleData);
        window.removeEventListener("resize", this.handleResize);
        this.disposeCharts();
        this.container?.remove();
        this.map = null;
        this.container = null;
    }

    currentStyleKey() {
        return this.activeStyleKey
            || this.options.getActiveStyleKey?.()
            || Object.keys(this.config.themes || {})[0]
            || null;
    }

    setActiveStyle(styleKey) {
        this.activeStyleKey = styleKey;
        const theme = this.config.themes?.[styleKey];
        if (theme && this.button) {
            this.button.title = `Analyze ${theme.label}`;
            this.button.setAttribute("aria-label", `Analyze ${theme.label}`);
        }
        if (this.opened) this.scheduleRender(this.viewportInput?.checked ? 180 : 0);
    }

    toggle() {
        if (this.opened) this.close();
        else this.open();
    }

    open() {
        this.opened = true;
        this.panel?.classList.remove("is-hidden");
        this.button?.classList.add("is-active");
        this.button?.setAttribute("aria-expanded", "true");
        if (this.map) {
            this.map.fire('oswm-theme-chart-opened');
        }
        this.render();
    }

    close() {
        this.opened = false;
        this.panel?.classList.add("is-hidden");
        this.button?.classList.remove("is-active");
        this.button?.setAttribute("aria-expanded", "false");
        this.button?.focus();
    }

    scheduleRender(delay = 0) {
        clearTimeout(this.renderTimer);
        this.renderTimer = setTimeout(() => this.render(), delay);
    }

    async loadNodeSummary() {
        if (!this.config.summary_url) throw new Error("No precomputed summary URL is configured.");
        if (!this.summaryPromise) {
            this.summaryPromise = fetch(this.config.summary_url, { cache: "no-cache" })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Summary request failed with HTTP ${response.status}.`);
                    }
                    return response.json();
                });
        }
        return this.summaryPromise;
    }

    async ensureRenderer() {
        if (this.echarts?.init) return this.echarts;
        if (!this.options.loadECharts) {
            throw new Error("The chart renderer is not configured.");
        }
        if (!this.echartsPromise) {
            this.echartsPromise = Promise.resolve(this.options.loadECharts())
                .then((module) => {
                    const renderer = module?.init ? module : module?.default;
                    if (!renderer?.init) throw new Error("The chart renderer could not be loaded.");
                    this.echarts = renderer;
                    return renderer;
                });
        }
        return this.echartsPromise;
    }

    setLoading(message) {
        this.status.textContent = message;
        this.content.setAttribute("aria-busy", "true");
    }

    showMessage(message, isError = false) {
        this.disposeCharts();
        this.content.replaceChildren(
            createElement("p", isError ? "oswm-theme-chart-error" : "oswm-theme-chart-empty", message),
        );
        this.content.removeAttribute("aria-busy");
    }

    async render() {
        if (!this.opened || !this.map) return;
        const sequence = ++this.renderSequence;
        const styleKey = this.currentStyleKey();
        const theme = this.config.themes?.[styleKey];
        if (!theme) {
            this.title.textContent = "Theme unavailable";
            this.status.textContent = "No chart definition exists for this map style.";
            this.showMessage("Choose a thematic map style with analytical metadata.");
            return;
        }

        this.title.textContent = theme.label;
        const viewport = Boolean(this.viewportInput.checked);
        this.setLoading(viewport
            ? "Calculating a live estimate from visible vector tiles…"
            : "Loading the exact precomputed summary…");

        try {
            let summary;
            let statusText;
            if (viewport) {
                if (typeof this.map.isStyleLoaded === "function" && !this.map.isStyleLoaded()) {
                    this.status.textContent = "Waiting for the selected map style…";
                    this.scheduleRender(220);
                    return;
                }
                await this.ensureRenderer();
                summary = collectViewportThemeStats(this.map, theme);
                statusText = "Visible area · estimated from rendered vector tiles";
            } else {
                const [documentSummary] = await Promise.all([
                    this.loadNodeSummary(),
                    this.ensureRenderer(),
                ]);
                summary = documentSummary?.themes?.[styleKey];
                statusText = `Entire dataset · exact · ${formattedRevision(documentSummary?.generated_at)}`;
            }
            if (sequence !== this.renderSequence) return;
            if (!summary) throw new Error(`No summary is available for ${theme.label}.`);
            this.status.textContent = statusText;
            this.renderSummary(summary, theme);
        } catch (error) {
            if (sequence !== this.renderSequence) return;
            this.status.textContent = "Analysis unavailable";
            this.showMessage(error.message || "The chart could not be generated.", true);
            console.error("Webmap theme chart could not be generated:", error);
        }
    }

    disposeCharts() {
        if (!this.charts.length) return;
        this.charts.forEach((chart) => {
            if (chart.__oswm_observer) {
                chart.__oswm_observer.disconnect();
            }
            chart.dispose();
        });
        this.charts = [];
    }

    renderSummary(summary, theme) {
        this.disposeCharts();
        this.content.replaceChildren();
        const panels = summary.kind === "multi"
            ? summary.panels || []
            : [summary];
        const panelThemes = theme.kind === "multi"
            ? theme.panels || []
            : [theme];

        const chartsToInit = [];
        panels.forEach((panelSummary, index) => {
            const panelTheme = panelThemes[index] || panelSummary;
            const { section, chartElement, reducedMotion } = this.renderPanel(panelSummary, panelTheme, panels.length > 1);
            this.content.appendChild(section);
            if (chartElement) {
                chartsToInit.push({ chartElement, summary: panelSummary, theme: panelTheme, reducedMotion });
            }
        });
        if (!panels.length) this.showMessage("No analytical panels are configured for this theme.");
        this.content.removeAttribute("aria-busy");

        if (this.echarts?.init) {
            chartsToInit.forEach(({ chartElement, summary, theme, reducedMotion }) => {
                const chart = this.echarts.init(chartElement, null, { renderer: "svg" });
                chart.setOption(buildThemeChartOption(summary, theme, { reducedMotion }));
                this.charts.push(chart);
                
                // Ensure chart resizes when container gets its layout dimensions
                const observer = new ResizeObserver(() => {
                    chart.resize();
                });
                observer.observe(chartElement);
                // Save observer so it can be disconnected in disposeCharts()
                chart.__oswm_observer = observer;
            });
        } else {
            chartsToInit.forEach(({ chartElement }) => {
                chartElement.replaceChildren(createElement(
                    "p",
                    "oswm-theme-chart-error",
                    "The chart renderer could not be loaded.",
                ));
            });
        }
    }

    renderPanel(summary, theme, showHeading) {
        const section = createElement("section", "oswm-theme-chart-section");
        if (showHeading) section.appendChild(createElement("h3", "", theme.label));
        const rows = themeChartRows(summary, theme);
        const metric = themeMetricSummary(summary, theme);
        if (!rows.length) {
            section.appendChild(createElement(
                "p",
                "oswm-theme-chart-empty",
                "No rendered features are available for this scope.",
            ));
            return { section, chartElement: null };
        }

        const chartElement = createElement("div", "oswm-theme-chart-canvas");
        chartElement.style.height = summary.kind === "numeric"
            ? "238px"
            : `${Math.max(170, Math.min(350, rows.length * 30 + 62))}px`;
        chartElement.setAttribute("role", "img");
        chartElement.setAttribute("aria-label", `${theme.label}. ${metric.label}.`);
        section.appendChild(chartElement);

        const reducedMotion = Boolean(
            window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches,
        );

        section.appendChild(createElement("p", "oswm-theme-chart-metric", metric.label));
        section.appendChild(this.renderDataTable(rows));
        return { section, chartElement, reducedMotion };
    }

    renderDataTable(rows) {
        const details = createElement("details", "oswm-theme-chart-table-wrap");
        details.appendChild(createElement("summary", "", "Data table"));
        const table = document.createElement("table");
        const head = document.createElement("thead");
        const headRow = document.createElement("tr");
        ["Class", "Value", "%"].forEach((label) => {
            headRow.appendChild(createElement("th", "", label));
        });
        head.appendChild(headRow);
        const body = document.createElement("tbody");
        rows.forEach((row) => {
            const tableRow = document.createElement("tr");
            const digits = row.unit === "km" ? 2 : 0;
            [
                row.label,
                `${formatChartNumber(row.value, digits)} ${row.unit}`,
                `${formatChartNumber(row.percent, 1)}%`,
            ].forEach((value) => tableRow.appendChild(createElement("td", "", value)));
            body.appendChild(tableRow);
        });
        table.append(head, body);
        details.appendChild(table);
        return details;
    }
}

export function installThemeChartControl(map, params, options = {}) {
    const config = params?.theme_charts || params;
    if (!config?.themes || !Object.keys(config.themes).length) return null;
    const control = new ThemeChartControl(config, options);
    map.addControl(control, options.position || "bottom-left");
    return control;
}

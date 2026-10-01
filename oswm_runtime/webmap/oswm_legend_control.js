/**
 * OswmLegendControl — Native MapLibre IControl for OSWM.
 *
 * Provides:
 *  • Per-data-layer toggle checkboxes with color swatches
 *  • Style-specific symbology legend (pre-rendered HTML fragments)
 *
 * Replaces @watergis/maplibre-gl-legend with zero external dependencies.
 *
 * @example
 *   import { OswmLegendControl } from './oswm_legend_control.js';
 *   const ctrl = new OswmLegendControl(params, { initialStyle: 'footway_categories' });
 *   map.addControl(ctrl, 'top-right');
 */

export class OswmLegendControl {
    /**
     * @param {Object} params  - webmap_params (must include data_layers, layer_types, legend_fragments)
     * @param {Object} [options]
     * @param {string} [options.initialStyle] - active style key at construction time
     */
    constructor(params, options = {}) {
        this._params = params;
        this._options = options;
        this._container = null;
        this._panel = null;
        this._map = null;
        this._activeStyle = options.initialStyle || null;
        this._expanded = false;

        // Build a flat { layerId: 'line'|'fill'|'circle' } lookup
        this._layerTypeMap = {};
        const lt = params.layer_types || {};
        for (const [type, layers] of Object.entries(lt)) {
            for (const layer of layers) {
                this._layerTypeMap[layer] = type;
            }
        }
    }

    /* ── MapLibre IControl interface ─────────────────────────── */

    onAdd(map) {
        this._map = map;

        // Wrapper
        this._container = document.createElement('div');
        this._container.className = 'maplibregl-ctrl maplibregl-ctrl-group oswm-legend-ctrl';

        // Toggle button (legend icon)
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'oswm-legend-toggle-btn';
        btn.title = 'Toggle legend';
        btn.setAttribute('aria-label', 'Toggle legend panel');
        btn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
            <rect x="3" y="4" width="5" height="3" rx="0.5"/>
            <rect x="10" y="4" width="11" height="3" rx="0.5" opacity="0.4"/>
            <rect x="3" y="10.5" width="5" height="3" rx="0.5"/>
            <rect x="10" y="10.5" width="11" height="3" rx="0.5" opacity="0.4"/>
            <rect x="3" y="17" width="5" height="3" rx="0.5"/>
            <rect x="10" y="17" width="11" height="3" rx="0.5" opacity="0.4"/>
        </svg>`;
        btn.addEventListener('click', () => this.toggle());
        this._container.appendChild(btn);

        // Collapsible panel
        this._panel = document.createElement('div');
        this._panel.className = 'oswm-legend-panel';
        this._panel.style.display = 'none';
        this._container.appendChild(this._panel);

        this._buildPanel();

        return this._container;
    }

    onRemove() {
        this._container?.remove();
        this._container = null;
        this._panel = null;
        this._map = null;
    }

    /* ── Public API ──────────────────────────────────────────── */

    /**
     * Swap the active style. For the layer panel, we just need to wait
     * until the new style properties are applied to rebuild the swatches.
     */
    setActiveStyle(styleKey) {
        this._activeStyle = styleKey;
        if (this._map) {
            this._map.once('idle', () => this._buildPanel());
        }
    }

    /** Expand / collapse the panel. */
    toggle() {
        this._expanded = !this._expanded;
        this._panel.style.display = this._expanded ? 'block' : 'none';
        
        if (this._expanded && this._map) {
            this._map.fire('oswm-legend-opened');
        }

        // Notify external listener (used to sync the left-centered legend)
        if (this._options.onToggle) {
            this._options.onToggle(this._expanded);
        }
    }

    /** Close the panel if it is open. */
    close() {
        if (this._expanded) {
            this.toggle();
        }
    }

    /* ── Private helpers ─────────────────────────────────────── */

    _buildPanel() {
        if (!this._panel || !this._map) return;
        this._panel.innerHTML = '';

        // ── Header ──
        const header = document.createElement('div');
        header.className = 'oswm-legend-header';

        const title = document.createElement('span');
        title.className = 'oswm-legend-panel-title';
        title.textContent = 'Layers';
        header.appendChild(title);

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'oswm-legend-close-btn';
        closeBtn.title = 'Close';
        closeBtn.innerHTML = '×';
        closeBtn.addEventListener('click', () => this.toggle());
        header.appendChild(closeBtn);

        this._panel.appendChild(header);

        // ── Layer toggles ──
        const layerSection = document.createElement('div');
        layerSection.className = 'oswm-legend-layers';

        const dataLayers = this._params.data_layers || [];
        dataLayers.forEach(layerId => {
            const item = document.createElement('div');
            item.className = 'oswm-legend-layer-item';

            // Checkbox
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = true;
            checkbox.id = `oswm-toggle-${layerId}`;
            checkbox.addEventListener('change', () => {
                try {
                    this._map.setLayoutProperty(
                        layerId, 'visibility',
                        checkbox.checked ? 'visible' : 'none'
                    );
                } catch (err) {
                    console.warn(`Could not toggle layer "${layerId}":`, err);
                }
            });

            // Label wraps text
            const label = document.createElement('label');
            label.htmlFor = checkbox.id;

            const text = document.createElement('span');
            text.className = 'oswm-legend-layer-label';
            text.textContent = layerId.replace(/_/g, ' ');

            label.appendChild(text);

            item.appendChild(checkbox);
            item.appendChild(label);
            layerSection.appendChild(item);
        });

        this._panel.appendChild(layerSection);
    }


}

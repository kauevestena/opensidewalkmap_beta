import { SnapshotComposer } from "./snapshot_composer.js";

export class SnapshotControl {
    constructor(params, options = {}) {
        this.params = params;
        this.options = options;
        this.container = null;
        this.composer = null;
    }

    onAdd(map) {
        this.composer = new SnapshotComposer(map, this.params, this.options);
        this.container = document.createElement("div");
        this.container.className = "maplibregl-ctrl maplibregl-ctrl-group oswm-snapshot-control";
        const button = document.createElement("button");
        button.type = "button";
        button.className = "oswm-snapshot-control-button";
        button.title = "Create scrutiny map (PDF)";
        button.setAttribute("aria-label", "Create scrutiny map for printing or PDF");
        button.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M6 9V2h12v7h1a3 3 0 0 1 3 3v6h-4v4H6v-4H2v-6a3 3 0 0 1 3-3h1Zm2-5v5h8V4H8Zm8 16v-5H8v5h8Zm3-6a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"></path>
        </svg>`;
        button.addEventListener("click", () => this.composer.open());
        this.container.appendChild(button);
        return this.container;
    }

    onRemove() {
        this.composer?.destroy();
        this.container?.remove();
        this.container = null;
        this.composer = null;
    }
}

export function installSnapshotControl(map, params, options = {}) {
    const control = new SnapshotControl(params, options);
    map.addControl(control, options.position || "top-right");
    return control;
}

const MANIFEST_URL = new URL("./manifest.json", import.meta.url);
const CODEBASE_ROOT_URL = new URL("../../", import.meta.url);

let manifestPromise = null;

export function resolveBrandingPath(manifest, semanticKey) {
    const parts = String(semanticKey || "").split(".").filter(Boolean);
    let value = manifest;
    for (const part of parts) {
        if (!value || typeof value !== "object" || !(part in value)) {
            throw new Error(`Unknown OSWM branding key: ${semanticKey}`);
        }
        value = value[part];
    }
    if (typeof value !== "string") {
        throw new Error(`OSWM branding key is not an asset: ${semanticKey}`);
    }
    return value;
}

export function loadBrandingManifest() {
    if (!manifestPromise) {
        manifestPromise = fetch(MANIFEST_URL, { cache: "no-store" }).then((response) => {
            if (!response.ok) {
                throw new Error(`OSWM branding manifest is unavailable (HTTP ${response.status}).`);
            }
            return response.json();
        });
    }
    return manifestPromise;
}

export async function brandingAssetUrl(semanticKey) {
    const manifest = await loadBrandingManifest();
    return new URL(resolveBrandingPath(manifest, semanticKey), CODEBASE_ROOT_URL).href;
}

export async function applyBranding(root = document) {
    const elements = [...root.querySelectorAll("[data-oswm-branding]")];
    await Promise.all(elements.map(async (element) => {
        const semanticKey = element.dataset.oswmBranding;
        const attribute = element.dataset.oswmBrandingAttribute
            || (element.tagName === "LINK" ? "href" : "src");
        try {
            element.setAttribute(attribute, await brandingAssetUrl(semanticKey));
        } catch (_error) {
            element.dataset.oswmBrandingError = "true";
        }
    }));
}

if (typeof document !== "undefined") {
    const apply = () => applyBranding().catch(() => {});
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", apply, { once: true });
    } else {
        apply();
    }
}

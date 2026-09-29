"""Generate a standalone HTML classification guide from the hazard rules.

Re-run this script whenever ``rules.py`` is updated so the public
documentation stays in sync with the live policy.

Usage from the repository root:

    PYTHONPATH=oswm_codebase python -m hazard_analysis.generate_classification_guide

The generated file is written next to hazard_analysis.html so it can be
linked with a simple relative URL.
"""

from __future__ import annotations

import html
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from the repository root with PYTHONPATH=oswm_codebase
_this_dir = Path(__file__).resolve().parent
_codebase_dir = _this_dir.parent
if str(_codebase_dir) not in sys.path:
    sys.path.insert(0, str(_codebase_dir))

from hazard_analysis.rules import (
    HAZARD_CATEGORIES,
    HAZARD_PROFILES,
    HAZARD_RULES,
    HAZARD_RULESET_VERSION,
    SEVERITY_LEVELS,
)
from hazard_analysis.validation import ruleset_hash, validate_rules

OUTPUT_PATH = _this_dir / "classification_guide.html"

_esc = html.escape

def _severity_color(level: int) -> str:
    return SEVERITY_LEVELS.get(level, {}).get("color", "#9e9e9e")


def _traversability_badge(traversability: str) -> str:
    colors = {
        "passable": ("#e8f5e9", "#2e7d32"),
        "passable_with_extreme_risk": ("#fff3e0", "#e65100"),
        "impassable": ("#ffebee", "#b71c1c"),
    }
    bg, fg = colors.get(traversability, ("#f5f5f5", "#424242"))
    label = traversability.replace("_", " ").capitalize()
    return (
        f'<span class="trav-badge" style="background:{bg};color:{fg}">'
        f"{_esc(label)}</span>"
    )


def _severity_pill(level: int) -> str:
    meta = SEVERITY_LEVELS.get(level, {})
    color = _severity_color(level)
    label = meta.get("label", "Unknown")
    extra_style = "color:#1a1d20;border:1px solid #d8dde2;" if level == 0 else ""
    return (
        f'<span class="severity-pill" style="background:{_esc(color)};{extra_style}">'
        f"{level} — {_esc(label)}</span>"
    )


def _profile_icon(profile_id: str) -> str:
    icons = {
        "pedestrian": "🚶",
        "wheelchair": "♿",
        "blind": "🦯",
        "elderly": "🧓",
    }
    return icons.get(profile_id, "👤")


def _build_severity_table() -> str:
    rows = []
    for level, meta in SEVERITY_LEVELS.items():
        rows.append(
            f"<tr>"
            f'<td class="center">{_severity_pill(level)}</td>'
            f"<td>{_esc(meta['description'])}</td>"
            f"</tr>"
        )
    return (
        '<table class="ref-table">'
        "<thead><tr><th>Level</th><th>Meaning</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _build_category_table() -> str:
    rows = []
    for cat_id, cat in HAZARD_CATEGORIES.items():
        rows.append(
            f"<tr><td><code>{_esc(cat_id)}</code></td>"
            f"<td><strong>{_esc(cat['label'])}</strong></td>"
            f"<td>{_esc(cat['description'])}</td></tr>"
        )
    return (
        '<table class="ref-table">'
        "<thead><tr><th>ID</th><th>Label</th><th>Description</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _build_profile_cards() -> str:
    cards = []
    for pid, pmeta in HAZARD_PROFILES.items():
        cards.append(
            f'<div class="profile-card">'
            f'<span class="profile-icon">{_profile_icon(pid)}</span>'
            f"<div>"
            f"<strong>{_esc(pmeta['label'])}</strong><br>"
            f'<span class="dim">{_esc(pmeta["description"])}</span>'
            f"</div></div>"
        )
    return "".join(cards)


def _condition_summary(rule: dict) -> str:
    cond = rule["condition"]
    op = cond.get("operator", "")
    field = cond.get("field", "")
    applies = rule.get("applies_to")

    scope = ""
    if applies:
        scope = " · applies to: " + ", ".join(
            f"<code>{_esc(a)}</code>" for a in applies
        )

    if op == "equals":
        return f"<code>{_esc(field)}</code> = <code>{_esc(str(cond['value']))}</code>{scope}"
    if op == "in":
        vals = ", ".join(f"<code>{_esc(v)}</code>" for v in cond["value"])
        return f"<code>{_esc(field)}</code> ∈ {{{vals}}}{scope}"
    if op == "contains":
        return f"<code>{_esc(field)}</code> contains <code>{_esc(str(cond['value']))}</code>{scope}"
    if op == "transition_pair":
        return (
            f"<code>{_esc(field)}</code> has pair: "
            f"kerb=<code>{_esc(cond['kerb'])}</code>, "
            f"tactile_paving=<code>{_esc(cond['tactile_paving'])}</code>{scope}"
        )
    if op in ("gt", "lt"):
        symbol = "&gt;" if op == "gt" else "&lt;"
        return f"<code>{_esc(field)}</code> {symbol} {cond['value']}{scope}"
    if op == "abs_gt":
        return f"|<code>{_esc(field)}</code>| &gt; {cond['value']}{scope}"
    if op == "range":
        return (
            f"{cond['min_exclusive']} &lt; <code>{_esc(field)}</code> "
            f"≤ {cond['max_inclusive']}{scope}"
        )
    if op == "abs_range":
        return (
            f"{cond['min_exclusive']} &lt; |<code>{_esc(field)}</code>| "
            f"≤ {cond['max_inclusive']}{scope}"
        )
    if op == "negative_range":
        return (
            f"{cond['min_abs_exclusive']} &lt; |<code>{_esc(field)}</code>| "
            f"≤ {cond['max_abs_inclusive']} (descent){scope}"
        )
    return f"<code>{_esc(field)}</code> {_esc(op)} …{scope}"


def _build_rule_cards() -> str:
    by_category: dict[str, list[dict]] = {}
    for rule in HAZARD_RULES:
        by_category.setdefault(rule["category"], []).append(rule)

    sections = []
    for cat_id, cat_meta in HAZARD_CATEGORIES.items():
        rules = by_category.get(cat_id, [])
        if not rules:
            continue
        cards_html = []
        for rule in rules:
            directional = rule.get("directional", False)
            dir_badge = (
                ' <span class="dir-badge">⇅ directional</span>'
                if directional
                else ""
            )

            # Collect affected profile IDs as data attributes for filtering
            affected_profiles = " ".join(rule["effects"].keys())

            effect_rows = []
            for pid, eff in rule["effects"].items():
                pmeta = HAZARD_PROFILES.get(pid, {})
                effect_rows.append(
                    f"<tr>"
                    f'<td class="profile-cell">{_profile_icon(pid)} '
                    f"{_esc(pmeta.get('label', pid))}</td>"
                    f"<td>{_severity_pill(eff['severity'])}</td>"
                    f"<td>{_esc(eff['impact'])}</td>"
                    f"<td>{_traversability_badge(eff['traversability'])}</td>"
                    f"</tr>"
                )
            effects_table = (
                '<table class="effects-table">'
                "<thead><tr><th>Profile</th><th>Severity</th>"
                "<th>Impact</th><th>Traversability</th></tr></thead>"
                f"<tbody>{''.join(effect_rows)}</tbody></table>"
            )

            cards_html.append(
                f'<div class="rule-card" '
                f'data-category="{_esc(rule["category"])}" '
                f'data-profiles="{_esc(affected_profiles)}" '
                f'data-rule-id="{_esc(rule["id"])}" '
                f'data-description="{_esc(rule["description"].lower())}">'
                f'<div class="rule-header">'
                f'<span class="rule-id"><code>{_esc(rule["id"])}</code></span>'
                f'{dir_badge}'
                f'<span class="confidence-badge">{rule["confidence"]}% confidence</span>'
                f"</div>"
                f'<p class="rule-desc">{_esc(rule["description"])}</p>'
                f'<div class="rule-condition">'
                f"<strong>Condition:</strong> {_condition_summary(rule)}"
                f"</div>"
                f"{effects_table}"
                f"</div>"
            )

        sections.append(
            f'<section class="cat-section" id="cat-{_esc(cat_id)}">'
            f"<h3>{_esc(cat_meta['label'])}</h3>"
            f'<p class="cat-desc">{_esc(cat_meta["description"])}</p>'
            f"{''.join(cards_html)}"
            f"</section>"
        )

    return "".join(sections)


def _build_nav_links() -> str:
    links = []
    for cat_id, cat_meta in HAZARD_CATEGORIES.items():
        links.append(
            f'<a href="#cat-{_esc(cat_id)}">{_esc(cat_meta["label"])}</a>'
        )
    return " · ".join(links)


def _build_filter_checkboxes() -> str:
    """Category and profile checkboxes for interactive rule filtering."""
    cat_checks = []
    for cat_id, cat_meta in HAZARD_CATEGORIES.items():
        cat_checks.append(
            f'<label class="filter-chip">'
            f'<input type="checkbox" class="filter-cat" value="{_esc(cat_id)}" checked> '
            f"{_esc(cat_meta['label'])}</label>"
        )
    prof_checks = []
    for pid, pmeta in HAZARD_PROFILES.items():
        prof_checks.append(
            f'<label class="filter-chip">'
            f'<input type="checkbox" class="filter-prof" value="{_esc(pid)}" checked> '
            f"{_profile_icon(pid)} {_esc(pmeta['label'])}</label>"
        )
    return (
        '<details class="filter-panel" id="filterPanel">'
        "<summary>Filter by category / profile</summary>"
        '<div class="filter-group">'
        '<div class="filter-label">Categories</div>'
        f'<div class="filter-chips">{"".join(cat_checks)}</div>'
        "</div>"
        '<div class="filter-group">'
        '<div class="filter-label">Profiles</div>'
        f'<div class="filter-chips">{"".join(prof_checks)}</div>'
        "</div>"
        '<div class="filter-actions">'
        '<button type="button" class="small-btn" id="filterSelectAll">Select all</button> '
        '<button type="button" class="small-btn" id="filterClearAll">Clear all</button>'
        "</div>"
        "</details>"
    )


def generate() -> str:
    validate_rules(HAZARD_RULES)
    rules_hash = ruleset_hash(HAZARD_RULES)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSWM Hazard Classification Guide</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Kdam+Thmor+Pro&display=swap" rel="stylesheet">
    <script type="module" src="../assets/branding/branding.js"></script>
    <link rel="icon" data-oswm-branding="favicon">
    <style>
        :root {{
            --bg: #f8f9fb; --card: #ffffff; --border: #e2e6ea;
            --text: #1f2933; --dim: #59636e; --accent: #165a72;
            --accent-light: #e8f4f8;
        }}
        *, *::before, *::after {{ box-sizing: border-box; }}
        html {{ scroll-behavior: smooth; }}
        body {{
            margin: 0; font-family: Inter, "Helvetica Neue", Arial, sans-serif;
            background: var(--bg); color: var(--text); line-height: 1.6;
        }}
        .page {{ max-width: 960px; margin: 0 auto; padding: 20px 24px 60px; }}

        /* ── Top bar ── */
        .top-bar {{
            background: var(--accent); color: white; padding: 12px 24px;
            display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
        }}
        .top-bar .brand {{
            display: flex; align-items: center; gap: 10px;
            text-decoration: none; color: white;
        }}
        .top-bar .brand img {{ height: 36px; }}
        .top-bar .brand-name {{
            font-family: 'Kdam Thmor Pro', sans-serif;
            font-size: 18px; letter-spacing: .02em;
        }}
        .top-bar a {{ color: white; text-decoration: none; font-weight: 600; }}
        .top-bar .spacer {{ flex: 1; }}
        .top-bar .back-link {{ font-size: 13px; opacity: .85; }}

        /* ── Headings ── */
        h1 {{ font-size: 28px; margin: 24px 0 6px; }}
        h3 {{ font-size: 18px; margin: 22px 0 8px; }}
        .meta {{ color: var(--dim); font-size: 13px; margin-bottom: 18px; }}

        /* ── Collapsible h2 sections ── */
        .section-collapse {{
            border: none; margin: 22px 0 6px;
        }}
        .section-collapse > summary {{
            font-size: 21px; font-weight: 700;
            cursor: pointer; list-style: none; user-select: none;
            padding-bottom: 6px; border-bottom: 2px solid var(--border);
            display: flex; align-items: center; gap: 8px;
        }}
        .section-collapse > summary::-webkit-details-marker {{ display: none; }}
        .section-collapse > summary::before {{
            content: '▸'; font-size: 16px; transition: transform .2s;
            display: inline-block; width: 16px; color: var(--dim);
        }}
        .section-collapse[open] > summary::before {{
            transform: rotate(90deg);
        }}
        .section-collapse > .section-body {{
            padding-top: 8px;
        }}

        /* ── Disclaimer ── */
        .disclaimer {{
            background: #fff3cd; border-left: 4px solid #ffc107;
            padding: 12px 16px; border-radius: 6px; margin: 18px 0;
            font-size: 14px; line-height: 1.5;
        }}

        /* ── Nav links ── */
        .nav {{ margin: 14px 0; font-size: 14px; }}
        .nav a {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
        .nav a:hover {{ text-decoration: underline; }}

        /* ── Profile cards ── */
        .profiles {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 12px 0; }}
        .profile-card {{
            display: flex; gap: 10px; align-items: center;
            background: var(--card); border: 1px solid var(--border);
            border-radius: 8px; padding: 10px 14px; flex: 1 1 200px; min-width: 200px;
        }}
        .profile-icon {{ font-size: 28px; }}
        .dim {{ color: var(--dim); font-size: 13px; }}

        /* ── Reference tables ── */
        .ref-table {{
            width: 100%; border-collapse: collapse; margin: 10px 0 16px;
            font-size: 14px;
        }}
        .ref-table th {{ text-align: left; padding: 8px 10px; background: var(--accent-light); }}
        .ref-table td {{ padding: 8px 10px; border-bottom: 1px solid var(--border); }}
        .ref-table code {{ background: #f0f2f4; padding: 1px 5px; border-radius: 3px; font-size: 13px; }}
        .center {{ text-align: center; }}

        /* ── Search box ── */
        .search-box {{
            width: 100%; padding: 10px 14px; border: 1px solid var(--border);
            border-radius: 8px; font-size: 14px; background: var(--card);
            margin: 10px 0 6px; outline: none;
        }}
        .search-box:focus {{ border-color: var(--accent); box-shadow: 0 0 0 2px rgba(22,90,114,.15); }}
        .search-status {{
            font-size: 12px; color: var(--dim); margin-bottom: 10px;
        }}

        /* ── Filter checkboxes panel ── */
        .filter-panel {{
            border: 1px solid var(--border); border-radius: 8px;
            background: var(--card); margin: 8px 0 14px; overflow: hidden;
        }}
        .filter-panel > summary {{
            padding: 10px 14px; cursor: pointer; font-size: 13px;
            font-weight: 700; color: var(--accent); user-select: none;
            list-style: none;
        }}
        .filter-panel > summary::-webkit-details-marker {{ display: none; }}
        .filter-panel > summary::before {{
            content: '▸ '; display: inline-block; transition: transform .15s;
        }}
        .filter-panel[open] > summary::before {{
            transform: rotate(90deg);
        }}
        .filter-group {{ padding: 4px 14px 8px; }}
        .filter-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase;
            letter-spacing: .04em; color: var(--dim); margin-bottom: 6px; }}
        .filter-chips {{ display: flex; flex-wrap: wrap; gap: 6px 10px; }}
        .filter-chip {{
            display: inline-flex; align-items: center; gap: 4px;
            font-size: 13px; cursor: pointer; user-select: none;
        }}
        .filter-chip input {{ margin: 0; }}
        .filter-actions {{ padding: 4px 14px 12px; display: flex; gap: 8px; }}
        .small-btn {{
            padding: 4px 10px; font-size: 12px; border: 1px solid var(--border);
            border-radius: 5px; background: var(--card); cursor: pointer;
            color: var(--accent); font-weight: 600;
        }}
        .small-btn:hover {{ background: var(--accent-light); }}

        /* ── Category sections ── */
        .cat-section {{ margin-top: 24px; }}
        .cat-section.hidden-section {{ display: none; }}
        .cat-desc {{ color: var(--dim); font-size: 14px; margin: 0 0 14px; }}

        /* ── Rule cards ── */
        .rule-card {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 10px; padding: 16px 18px; margin-bottom: 14px;
        }}
        .rule-card.hidden-card {{ display: none; }}
        .rule-header {{
            display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
            margin-bottom: 6px;
        }}
        .rule-id code {{
            font-size: 14px; font-weight: 700; background: var(--accent-light);
            padding: 2px 8px; border-radius: 4px; color: var(--accent);
        }}
        .dir-badge {{
            font-size: 11px; background: #e3f2fd; color: #1565c0;
            padding: 2px 7px; border-radius: 999px; font-weight: 700;
        }}
        .confidence-badge {{
            margin-left: auto; font-size: 12px; color: var(--dim); font-weight: 600;
        }}
        .rule-desc {{ margin: 4px 0 10px; font-size: 14px; }}
        .rule-condition {{
            font-size: 13px; background: #f5f6f8; padding: 8px 12px;
            border-radius: 6px; margin-bottom: 12px;
        }}
        .rule-condition code {{ background: #e8eaed; padding: 1px 4px; border-radius: 3px; }}

        /* ── Effects table ── */
        .effects-table {{
            width: 100%; border-collapse: collapse; font-size: 13px;
        }}
        .effects-table th {{
            text-align: left; padding: 6px 8px; background: #f9fafb;
            font-weight: 700; font-size: 12px; text-transform: uppercase;
            letter-spacing: .03em; border-bottom: 2px solid var(--border);
        }}
        .effects-table td {{ padding: 7px 8px; border-bottom: 1px solid #eef0f3; }}
        .profile-cell {{ white-space: nowrap; }}

        /* ── Severity pills and badges ── */
        .severity-pill {{
            display: inline-block; padding: 2px 9px; border-radius: 999px;
            color: white; font-size: 12px; font-weight: 700; white-space: nowrap;
        }}
        .trav-badge {{
            display: inline-block; padding: 2px 8px; border-radius: 999px;
            font-size: 11px; font-weight: 600; white-space: nowrap;
        }}

        /* ── Footer ── */
        .guide-footer {{
            margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border);
            font-size: 12px; color: var(--dim);
        }}

        @media (max-width: 600px) {{
            .page {{ padding: 14px 12px 40px; }}
            h1 {{ font-size: 22px; }}
            .rule-header {{ flex-direction: column; align-items: flex-start; }}
            .confidence-badge {{ margin-left: 0; }}
            .effects-table {{ font-size: 12px; }}
            .top-bar .brand-name {{ font-size: 15px; }}
        }}
    </style>
</head>
<body>
    <div class="top-bar">
        <a class="brand" href="../../index.html">
            <img src="../assets/branding/logos/project_logo_100px.png" alt="OSWM logo">
            <span class="brand-name">OpenSidewalkMap</span>
        </a>
        <span class="spacer"></span>
        <a class="back-link" href="hazard_analysis.html">← Back to Hazard Analysis Map</a>
    </div>

    <div class="page">
        <h1>Hazard Classification Guide</h1>
        <div class="meta">
            Ruleset version {_esc(HAZARD_RULESET_VERSION)} ·
            hash <code>{_esc(rules_hash)}</code> ·
            {len(HAZARD_RULES)} rules ·
            generated {_esc(timestamp)}
        </div>

        <div class="disclaimer">
            <strong>⚠ Screening tool — not a safety certification.</strong>
            These rules are provisional. A feature with no detected hazard is
            <strong>not certified safe</strong>. Missing data is never treated as
            evidence of absence. Severity levels, confidence scores and
            surface-material proxies require participatory calibration.
        </div>

        <details class="section-collapse" open>
            <summary>User Profiles</summary>
            <div class="section-body">
                <p>Each rule may affect one or more profiles differently:</p>
                <div class="profiles">{_build_profile_cards()}</div>
            </div>
        </details>

        <details class="section-collapse" open>
            <summary>Severity Levels</summary>
            <div class="section-body">
                {_build_severity_table()}
            </div>
        </details>

        <details class="section-collapse" open>
            <summary>Hazard Categories</summary>
            <div class="section-body">
                {_build_category_table()}
            </div>
        </details>

        <details class="section-collapse" id="rulesSection" open>
            <summary>Classification Rules</summary>
            <div class="section-body">
                <input type="text" class="search-box" id="ruleSearch"
                       placeholder="Search rules by ID, description or condition…"
                       autocomplete="off">
                {_build_filter_checkboxes()}
                <div class="nav">Jump to: {_build_nav_links()}</div>
                <div class="search-status" id="searchStatus"></div>
                <div id="rulesContainer">
                    {_build_rule_cards()}
                </div>
            </div>
        </details>

        <div class="guide-footer">
            OSWM Hazard Analysis Classification Guide · auto-generated from
            <code>hazard_analysis/rules.py</code> ·
            <a href="https://github.com/kauevestena/oswm_codebase">source</a>
        </div>
    </div>

    <script>
    (function() {{
        const search = document.getElementById('ruleSearch');
        const status = document.getElementById('searchStatus');
        const cards = document.querySelectorAll('.rule-card');
        const sections = document.querySelectorAll('.cat-section');
        const catChecks = document.querySelectorAll('.filter-cat');
        const profChecks = document.querySelectorAll('.filter-prof');

        function applyFilters() {{
            const query = search.value.trim().toLowerCase();
            const activeCats = new Set(
                [...catChecks].filter(c => c.checked).map(c => c.value)
            );
            const activeProfs = new Set(
                [...profChecks].filter(c => c.checked).map(c => c.value)
            );
            let visible = 0;
            cards.forEach(card => {{
                const cat = card.dataset.category;
                const profs = card.dataset.profiles.split(' ');
                const rid = card.dataset.ruleId;
                const desc = card.dataset.description;

                const catOk = activeCats.has(cat);
                const profOk = profs.some(p => activeProfs.has(p));
                let searchOk = true;
                if (query) {{
                    searchOk = rid.includes(query) || desc.includes(query)
                        || card.textContent.toLowerCase().includes(query);
                }}
                const show = catOk && profOk && searchOk;
                card.classList.toggle('hidden-card', !show);
                if (show) visible++;
            }});
            sections.forEach(sec => {{
                const hasVisible = sec.querySelector('.rule-card:not(.hidden-card)');
                sec.classList.toggle('hidden-section', !hasVisible);
            }});
            if (query || activeCats.size < catChecks.length || activeProfs.size < profChecks.length) {{
                status.textContent = `Showing ${{visible}} of ${{cards.length}} rules`;
            }} else {{
                status.textContent = '';
            }}
        }}

        search.addEventListener('input', applyFilters);
        catChecks.forEach(c => c.addEventListener('change', applyFilters));
        profChecks.forEach(c => c.addEventListener('change', applyFilters));

        document.getElementById('filterSelectAll').addEventListener('click', () => {{
            catChecks.forEach(c => c.checked = true);
            profChecks.forEach(c => c.checked = true);
            applyFilters();
        }});
        document.getElementById('filterClearAll').addEventListener('click', () => {{
            catChecks.forEach(c => c.checked = false);
            profChecks.forEach(c => c.checked = false);
            applyFilters();
        }});
    }})();
    </script>
</body>
</html>
"""


def main() -> None:
    content = generate()
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"Classification guide written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

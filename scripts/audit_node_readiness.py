#!/usr/bin/env python3
"""Audit an OSWM node checkout without importing geospatial dependencies."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


GITHUB_FILE_LIMIT = 100 * 1024 * 1024
FILE_LIMIT_GUARD = 95 * 1024 * 1024
LARGE_FILE_WARNING = 50 * 1024 * 1024

REQUIRED_GENERATED_FILES = (
    "data/boundaries/infos.json",
    "data/boundaries/polygon.geojson",
    "data/boundaries/polygon.parquet",
    "data/raw/sidewalks.parquet",
    "data/raw/crossings.parquet",
    "data/raw/kerbs.parquet",
    "data/raw/other_footways.parquet",
    "data/processed/sidewalks.parquet",
    "data/processed/crossings.parquet",
    "data/processed/kerbs.parquet",
    "data/processed/other_footways.parquet",
    "data/tiles/sidewalks.pmtiles",
    "data/tiles/crossings.pmtiles",
    "data/tiles/kerbs.pmtiles",
    "data/tiles/tile_generation_report.json",
    "data/routing/profiles.json",
    "data/routing/metadata.json",
    "data/hazard_analysis/profiles.json",
    "data/hazard_analysis/metadata.json",
    "data/hazard_analysis/hazard.pmtiles",
    "data/snapshots/node_summary.json",
    "quality_check/index.json",
    "statistics/index.html",
    "hub/API/index.html",
    "index.html",
    "map.html",
    "webmap_params.json",
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    path: str | None = None


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def literal_config(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        if value_node is None:
            continue
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            try:
                values[target.id] = ast.literal_eval(value_node)
            except (ValueError, TypeError):
                pass
    return values


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def git_output(root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def add(
    findings: list[Finding],
    severity: str,
    code: str,
    message: str,
    path: str | None = None,
) -> None:
    findings.append(Finding(severity, code, message, path))


def bbox_overlap_ratio(a: list[float], b: list[float]) -> float:
    # Inputs use GeoJSON order: west, south, east, north.
    west = max(a[0], b[0])
    south = max(a[1], b[1])
    east = min(a[2], b[2])
    north = min(a[3], b[3])
    intersection = max(0.0, east - west) * max(0.0, north - south)
    reference = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return intersection / reference if reference else 0.0


def validate_config(root: Path, config: dict[str, Any], findings: list[Finding]) -> None:
    required = (
        "CITY_NAME",
        "CITY_SHORTNAME",
        "USERNAME",
        "REPO_NAME",
        "BOUNDING_BOX",
        "MID_LAT",
        "MID_LGT",
        "TILES_MIN_ZOOM",
        "TILES_MAX_ZOOM",
    )
    missing = [key for key in required if key not in config]
    if missing:
        add(findings, "error", "config.missing", f"Missing config values: {', '.join(missing)}", "config.py")
        return

    shortname = str(config["CITY_SHORTNAME"])
    if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", shortname):
        add(findings, "error", "config.shortname", f"Invalid CITY_SHORTNAME: {shortname!r}", "config.py")

    bbox = config["BOUNDING_BOX"]
    if not isinstance(bbox, (tuple, list)) or len(bbox) != 4:
        add(findings, "error", "config.bbox", "BOUNDING_BOX must contain south, west, north, east", "config.py")
        return
    south, west, north, east = map(float, bbox)
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        add(findings, "error", "config.bbox_order", f"Invalid BOUNDING_BOX ordering/range: {bbox}", "config.py")
    if not (south <= float(config["MID_LAT"]) <= north and west <= float(config["MID_LGT"]) <= east):
        add(findings, "error", "config.midpoint", "Configured midpoint is outside BOUNDING_BOX", "config.py")
    if int(config["TILES_MIN_ZOOM"]) > int(config["TILES_MAX_ZOOM"]):
        add(findings, "error", "config.zoom", "TILES_MIN_ZOOM exceeds TILES_MAX_ZOOM", "config.py")


def validate_identity(root: Path, config: dict[str, Any], findings: list[Finding]) -> None:
    city = str(config.get("CITY_NAME", ""))
    repo = str(config.get("REPO_NAME", ""))
    username = str(config.get("USERNAME", ""))
    expected_url = f"https://{username}.github.io/{repo}/"
    south, west, north, east = map(float, config.get("BOUNDING_BOX", (0, 0, 0, 0)))
    expected_bbox = [west, south, east, north]

    checks = (
        ("data/boundaries/infos.json", "name", city),
        ("data/snapshots/node_summary.json", "node_name", city),
        ("data/index.json", "node_name", city),
        ("data/index.json", "repository", repo),
        ("data/index.json", "base_url", expected_url),
        ("hub/acquisition/results.json", "node_name", city),
    )
    for relative, key, expected in checks:
        path = root / relative
        if not path.exists():
            continue
        payload = load_json(path)
        actual = payload.get(key) if isinstance(payload, dict) else None
        if actual != expected:
            add(
                findings,
                "error",
                "identity.mismatch",
                f"{key} is {actual!r}; expected {expected!r}",
                relative,
            )

    boundary_path = root / "data/boundaries/infos.json"
    boundary = load_json(boundary_path) if boundary_path.exists() else None
    if isinstance(boundary, dict) and isinstance(boundary.get("bbox"), list):
        try:
            ratio = bbox_overlap_ratio(list(map(float, boundary["bbox"])), expected_bbox)
        except (TypeError, ValueError):
            ratio = 0.0
        if ratio < 0.5:
            add(
                findings,
                "error",
                "identity.boundary",
                f"Generated boundary overlaps only {ratio:.1%} of the configured fallback bbox",
                "data/boundaries/infos.json",
            )

    params_path = root / "webmap_params.json"
    params = load_json(params_path) if params_path.exists() else None
    if isinstance(params, dict):
        actual_url = params.get("node_url", params.get("node_homepage"))
        if actual_url != expected_url:
            add(
                findings,
                "error",
                "identity.webmap_url",
                f"Webmap node URL is {actual_url!r}; expected {expected_url!r}",
                "webmap_params.json",
            )
        bounds = params.get("bounds")
        if isinstance(bounds, list) and len(bounds) == 4:
            try:
                ratio = bbox_overlap_ratio(list(map(float, bounds)), expected_bbox)
            except (TypeError, ValueError):
                ratio = 0.0
            if ratio < 0.5:
                add(
                    findings,
                    "error",
                    "identity.webmap_bounds",
                    f"Webmap bounds overlap only {ratio:.1%} of the configured fallback bbox",
                    "webmap_params.json",
                )

    for relative, marker in (
        ("README.md", "<CITYNAME>"),
        ("index.html", "<!--CITYNAME INSERTION-->"),
    ):
        path = root / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        pattern = re.escape(marker) + r"(.*?)" + re.escape(marker)
        match = re.search(pattern, text, flags=re.DOTALL)
        if match and match.group(1).strip() != city:
            add(
                findings,
                "error",
                "identity.marker",
                f"Embedded city is {match.group(1).strip()!r}; expected {city!r}",
                relative,
            )


def validate_submodule(root: Path, findings: list[Finding]) -> dict[str, str | None]:
    pinned_line = git_output(root, "ls-tree", "HEAD", "oswm_codebase")
    pinned = pinned_line.split()[2] if pinned_line and len(pinned_line.split()) >= 3 else None
    checked_out = git_output(root, "-C", "oswm_codebase", "rev-parse", "HEAD")
    if pinned is None:
        add(findings, "error", "submodule.pin", "No oswm_codebase gitlink is present", "oswm_codebase")
    elif checked_out is None:
        add(findings, "error", "submodule.checkout", "oswm_codebase is not initialized", "oswm_codebase")
    elif pinned != checked_out:
        add(
            findings,
            "error",
            "submodule.mismatch",
            f"Checked out {checked_out}; parent pins {pinned}",
            "oswm_codebase",
        )
    return {"pinned": pinned, "checked_out": checked_out}


def validate_workflows(root: Path, findings: list[Finding]) -> None:
    workflow_root = root / ".github/workflows"
    core_root = root / "oswm_codebase/workflows"
    if workflow_root.exists() and core_root.exists():
        for core_path in sorted(core_root.glob("*.yml")):
            node_path = workflow_root / core_path.name
            if not node_path.exists():
                add(findings, "warning", "workflow.missing", "Canonical workflow is absent from the node", str(node_path.relative_to(root)))
            elif node_path.read_bytes() != core_path.read_bytes():
                add(findings, "warning", "workflow.drift", "Node and oswm_codebase workflow copies differ", str(node_path.relative_to(root)))

    daily = workflow_root / "data_daily_updating.yml"
    if daily.exists():
        text = daily.read_text(encoding="utf-8")
        if "git commit --amend" in text or re.search(r"git push\s+--force(?:\s|$)", text):
            add(findings, "error", "workflow.force_push", "Daily updates rewrite main history with amend/force-push", str(daily.relative_to(root)))
        if re.search(r"^\s*ref:\s*main(?:\s+#.*)?$", text, flags=re.MULTILINE):
            add(findings, "warning", "workflow.hardcoded_main", "Manual dispatches always check out main, so feature-branch tests are unsafe", str(daily.relative_to(root)))
        if "FILE_LIMIT_GUARD" not in text and "100 * 1024 * 1024" not in text:
            add(findings, "warning", "workflow.file_limit", "Workflow does not gate generated files before GitHub's 100 MiB hard limit", str(daily.relative_to(root)))
        if re.search(r"cron:\s*[\"']?30 7 \* \* \*[\"']?", text):
            add(
                findings,
                "warning",
                "workflow.schedule_fanout",
                "Every cloned node inherits the same 07:30 UTC start; stagger schedules before a multi-node rollout",
                str(daily.relative_to(root)),
            )
        if re.search(r"^\s*TZ:\s*America/Sao_Paulo\s*$", text, flags=re.MULTILINE):
            add(
                findings,
                "warning",
                "workflow.timezone",
                "Node workflow timezone is hardcoded to America/Sao_Paulo",
                str(daily.relative_to(root)),
            )

    for path in sorted(workflow_root.glob("*.yml")) if workflow_root.exists() else ():
        text = path.read_text(encoding="utf-8")
        if "pip install -r requirements.txt" in text and not (root / "requirements.txt").exists():
            add(findings, "error", "workflow.requirements", "Workflow references missing root requirements.txt", str(path.relative_to(root)))
        if re.search(r"^\s*git add \.\s*$", text, flags=re.MULTILINE):
            add(findings, "warning", "workflow.stage_all", "Workflow stages the entire checkout rather than declared generated paths", str(path.relative_to(root)))


def validate_core_behaviors(root: Path, findings: list[Finding]) -> None:
    setup_path = root / "oswm_codebase/runners/setup.sh"
    if setup_path.exists():
        text = setup_path.read_text(encoding="utf-8", errors="replace")
        if "|| echo" in text:
            add(
                findings,
                "error",
                "runner.masked_failures",
                "Setup masks command failures and can report a successful shell exit when every step failed",
                str(setup_path.relative_to(root)),
            )

    special_path = root / "oswm_codebase/special_updates.py"
    if special_path.exists():
        text = special_path.read_text(encoding="utf-8", errors="replace")
        if "rmtree(workflows_path" in text and "copytree(" in text:
            add(
                findings,
                "error",
                "core.workflow_replacement",
                "Special updates delete the node workflow directory, including node-specific safeguards",
                str(special_path.relative_to(root)),
            )

    core_workflow_root = root / "oswm_codebase/workflows"
    if core_workflow_root.exists():
        core_workflow_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in sorted(core_workflow_root.glob("*.yml"))
        )
        if "git push" in core_workflow_text and "actions/deploy-pages@" not in core_workflow_text:
            add(
                findings,
                "error",
                "core.pages_deploy_missing",
                "Canonical workflows push generated output but contain no GitHub Pages deployment",
                str(core_workflow_root.relative_to(root)),
            )

    functions_path = root / "oswm_codebase/functions.py"
    watcher_path = root / "oswm_codebase/datahub/watcher/watcher_lib.py"
    if functions_path.exists() and watcher_path.exists():
        functions_text = functions_path.read_text(encoding="utf-8", errors="replace")
        watcher_text = watcher_path.read_text(encoding="utf-8", errors="replace")
        writes_naive_local = "now = datetime.now()" in functions_text and 'strftime("%d/%m/%Y %H:%M:%S")' in functions_text
        reads_as_utc = 'strptime(raw, "%d/%m/%Y %H:%M:%S").replace(' in watcher_text and "tzinfo=timezone.utc" in watcher_text
        if writes_naive_local and reads_as_utc:
            add(
                findings,
                "error",
                "timestamps.naive_as_utc",
                "Update timestamps are written in local naive time and later interpreted as UTC",
                str(watcher_path.relative_to(root)),
            )
        if "city_dems/1.0" in functions_text:
            add(
                findings,
                "warning",
                "nominatim.user_agent",
                "Nominatim requests identify an unrelated city_dems client instead of OSWM",
                str(functions_path.relative_to(root)),
            )

    requirements_path = root / "oswm_codebase/requirements.txt"
    if requirements_path.exists():
        requirements = [
            line.strip()
            for line in requirements_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        unbounded = [
            line
            for line in requirements
            if not re.search(r"(?:===|==|~=|!=|<=|>=|<|>|@)", line)
        ]
        if unbounded:
            add(
                findings,
                "warning",
                "dependencies.unbounded",
                f"All {len(unbounded)} runtime dependencies are unbounded; fresh node builds are not reproducible",
                str(requirements_path.relative_to(root)),
            )


def validate_files(
    root: Path,
    findings: list[Finding],
    *,
    require_generated: bool,
) -> dict[str, Any]:
    tracked = git_output(root, "ls-files", "-z")
    tracked_paths = [item for item in (tracked or "").split("\0") if item]
    candidates = git_output(
        root,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )
    paths = [item for item in (candidates or "").split("\0") if item]
    total = 0
    present_files = 0
    largest: list[tuple[int, str]] = []
    for relative in paths:
        path = root / relative
        if not path.is_file():
            continue
        present_files += 1
        size = path.stat().st_size
        total += size
        largest.append((size, relative))
        if size >= FILE_LIMIT_GUARD:
            add(
                findings,
                "error",
                "file.too_large",
                f"Commit candidate is {size / 1024 / 1024:.1f} MiB (guard {FILE_LIMIT_GUARD / 1024 / 1024:.0f} MiB)",
                relative,
            )
        elif size >= LARGE_FILE_WARNING:
            add(findings, "warning", "file.large", f"Commit candidate is {size / 1024 / 1024:.1f} MiB", relative)

    if require_generated:
        for relative in REQUIRED_GENERATED_FILES:
            path = root / relative
            if not path.is_file() or path.stat().st_size == 0:
                add(findings, "error", "output.missing", "Required generated output is missing or empty", relative)

    return {
        "tracked_files": len(tracked_paths),
        "commit_candidate_files": present_files,
        "commit_candidate_bytes": total,
        "github_file_limit_bytes": GITHUB_FILE_LIMIT,
        "largest": [
            {"path": relative, "bytes": size}
            for size, relative in sorted(largest, reverse=True)[:20]
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    counts = report["summary"]
    lines = [
        "# OSWM node launch-readiness audit",
        "",
        f"- City: `{report['config'].get('CITY_NAME', 'unknown')}`",
        f"- Repository: `{report['config'].get('USERNAME', 'unknown')}/{report['config'].get('REPO_NAME', 'unknown')}`",
        f"- Result: **{report['result'].upper()}**",
        f"- Findings: {counts['error']} errors, {counts['warning']} warnings, {counts['info']} informational",
        f"- Commit-candidate working-tree size: {report['files']['commit_candidate_bytes'] / 1024 / 1024:.1f} MiB",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("No findings.")
    for finding in report["findings"]:
        location = f" (`{finding['path']}`)" if finding.get("path") else ""
        lines.append(f"- **{finding['severity'].upper()} · {finding['code']}**{location}: {finding['message']}")
    lines.extend(("", "## Largest tracked files", ""))
    for entry in report["files"]["largest"][:10]:
        lines.append(f"- `{entry['path']}` — {entry['bytes'] / 1024 / 1024:.1f} MiB")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repository_root())
    parser.add_argument("--require-generated", action="store_true")
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="return failure when warnings are present",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    config = literal_config(root / "config.py")
    findings: list[Finding] = []
    validate_config(root, config, findings)
    if not any(item.code == "config.missing" for item in findings):
        validate_identity(root, config, findings)
    submodule = validate_submodule(root, findings)
    validate_workflows(root, findings)
    validate_core_behaviors(root, findings)
    files = validate_files(root, findings, require_generated=args.require_generated)

    counts = {
        severity: sum(item.severity == severity for item in findings)
        for severity in ("error", "warning", "info")
    }
    failed = counts["error"] > 0 or (args.warnings_as_errors and counts["warning"] > 0)
    report = {
        "schema_version": 1,
        "result": "fail" if failed else "pass",
        "config": {
            key: config.get(key)
            for key in (
                "CITY_NAME",
                "CITY_SHORTNAME",
                "USERNAME",
                "REPO_NAME",
                "BOUNDING_BOX",
                "MID_LAT",
                "MID_LGT",
                "TILES_MIN_ZOOM",
                "TILES_MAX_ZOOM",
            )
        },
        "submodule": submodule,
        "files": files,
        "summary": counts,
        "findings": [asdict(item) for item in findings],
    }

    rendered_json = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    print(rendered_json, end="")
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(rendered_json, encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown_report(report), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

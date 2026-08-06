#!/usr/bin/env python3
"""Dry-run-first wrapper around the core OSWM node-initialization contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

NODE_ROOT = Path(__file__).resolve().parents[1]
if str(NODE_ROOT) not in sys.path:
    sys.path.insert(0, str(NODE_ROOT))

from oswm_codebase.node_outputs import (
    INITIALIZATION_RESET_PATHS,
    reset_initialization,
    validate_node_root,
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def validate_root(root: Path) -> None:
    validate_node_root(root)
    if not (root / ".git").exists():
        raise RuntimeError("Refusing to reset a directory without Git metadata")


def path_size(path: Path) -> int:
    if path.is_file() or path.is_symlink():
        return path.stat().st_size
    return sum(
        candidate.stat().st_size
        for candidate in path.rglob("*")
        if candidate.is_file() and not candidate.is_symlink()
    )


def reset(root: Path, *, apply: bool) -> dict[str, object]:
    validate_root(root)
    targets = [root / relative for relative in INITIALIZATION_RESET_PATHS]
    existing = [path for path in targets if path.exists() or path.is_symlink()]
    removed_bytes = sum(path_size(path) for path in existing)
    core_report = reset_initialization(root, apply=apply)
    return {
        "mode": core_report["mode"],
        "root": str(root),
        "target_count": len(existing),
        "bytes": removed_bytes,
        "paths": core_report["paths"],
        "preserved": ["README.md", "index.html", "config.py", "oswm_codebase"],
        "contract": "oswm_codebase/node_outputs.py",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the reset; without this flag only print the plan",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=repository_root(),
        help="OSWM node checkout (defaults to the repository containing this script)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = reset(args.root.resolve(), apply=args.apply)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Remove generated products inherited from an OSWM template checkout.

The command is intentionally dry-run by default.  It preserves the homepage
and README source markers used by ``patch_readme_homepage.py`` and never touches
Git metadata, ``config.py``, or the ``oswm_codebase`` submodule.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


GENERATED_DIRECTORIES = (
    "data",
    "hub",
    "quality_check",
    "statistics",
    "statistics_specs",
)

GENERATED_FILES = (
    "map.html",
    "webmap_params.json",
    "run_log.txt",
    "run_log_full.txt",
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def validate_root(root: Path) -> None:
    required = (root / ".git", root / "config.py", root / "oswm_codebase")
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(
            "Refusing to reset a directory that is not an OSWM node checkout: "
            + ", ".join(missing)
        )
    if root == Path(root.anchor):
        raise RuntimeError("Refusing to operate on a filesystem root")


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
    targets = [root / value for value in (*GENERATED_DIRECTORIES, *GENERATED_FILES)]
    existing = [path for path in targets if path.exists() or path.is_symlink()]
    removed_bytes = sum(path_size(path) for path in existing)

    if apply:
        for path in existing:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()

        updates = root / "data" / "updates"
        updates.mkdir(parents=True, exist_ok=True)
        (updates / "registry.json").write_text("{}\n", encoding="utf-8")

    return {
        "mode": "apply" if apply else "dry-run",
        "root": str(root),
        "target_count": len(existing),
        "bytes": removed_bytes,
        "paths": [str(path.relative_to(root)) for path in existing],
        "preserved": ["README.md", "index.html", "config.py", "oswm_codebase"],
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

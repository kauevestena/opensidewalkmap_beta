#!/usr/bin/env python3
"""Dependency-free tests for the node launch-readiness helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_node_readiness import bbox_overlap_ratio, literal_config
from scripts.reset_node_outputs import reset


class ResetNodeOutputsTests(unittest.TestCase):
    def make_node(self, root: Path) -> None:
        (root / ".git").mkdir()
        (root / "oswm_codebase").mkdir()
        (root / "config.py").write_text('CITY_NAME = "Milan, Italy"\n', encoding="utf-8")
        (root / "README.md").write_text("source\n", encoding="utf-8")
        (root / "index.html").write_text("source\n", encoding="utf-8")
        (root / "data/raw").mkdir(parents=True)
        (root / "data/raw/inherited.parquet").write_bytes(b"old data")
        (root / "statistics").mkdir()
        (root / "statistics/obsolete.html").write_text("old\n", encoding="utf-8")
        (root / "map.html").write_text("old map\n", encoding="utf-8")

    def test_dry_run_does_not_mutate_and_apply_preserves_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_node(root)

            report = reset(root, apply=False)
            self.assertEqual(report["mode"], "dry-run")
            self.assertGreater(report["bytes"], 0)
            self.assertTrue((root / "data/raw/inherited.parquet").exists())

            report = reset(root, apply=True)
            self.assertEqual(report["mode"], "apply")
            self.assertFalse((root / "data/raw/inherited.parquet").exists())
            self.assertFalse((root / "statistics/obsolete.html").exists())
            self.assertFalse((root / "map.html").exists())
            self.assertEqual(
                json.loads((root / "data/updates/registry.json").read_text()),
                {},
            )
            self.assertTrue((root / "README.md").exists())
            self.assertTrue((root / "index.html").exists())
            self.assertTrue((root / "config.py").exists())
            self.assertTrue((root / "oswm_codebase").exists())

    def test_apply_is_repeatable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_node(root)
            reset(root, apply=True)
            reset(root, apply=True)
            self.assertEqual(
                (root / "data/updates/registry.json").read_text(encoding="utf-8"),
                "{}\n",
            )


class AuditHelpersTests(unittest.TestCase):
    def test_literal_config_does_not_execute_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.py"
            config.write_text(
                'CITY_NAME = "Milan, Italy"\nDYNAMIC = get_city()\n',
                encoding="utf-8",
            )
            self.assertEqual(literal_config(config), {"CITY_NAME": "Milan, Italy"})

    def test_bbox_overlap_uses_reference_area(self) -> None:
        self.assertEqual(bbox_overlap_ratio([0, 0, 1, 1], [2, 2, 3, 3]), 0.0)
        self.assertEqual(bbox_overlap_ratio([0, 0, 1, 1], [0, 0, 1, 1]), 1.0)


if __name__ == "__main__":
    unittest.main()

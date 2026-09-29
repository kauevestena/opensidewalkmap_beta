"""Validation and browser-safe publication for hazard policy dictionaries."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .rules import HAZARD_CATEGORIES, HAZARD_PROFILES, SEVERITY_LEVELS


def validate_rules(rules: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for index, rule in enumerate(rules):
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            raise ValueError(f"hazard rule {index} has no valid id")
        if rule_id in seen:
            raise ValueError(f"duplicate hazard rule id: {rule_id}")
        seen.add(rule_id)

        if rule.get("category") not in HAZARD_CATEGORIES:
            raise ValueError(f"{rule_id}: unknown category")
        confidence = rule.get("confidence")
        if not isinstance(confidence, int) or not 0 <= confidence <= 100:
            raise ValueError(f"{rule_id}: confidence must be an integer 0..100")
        if not isinstance(rule.get("condition"), Mapping):
            raise ValueError(f"{rule_id}: condition must be a mapping")
        applies_to = rule.get("applies_to", [])
        if not isinstance(applies_to, Sequence) or isinstance(applies_to, str):
            raise ValueError(f"{rule_id}: applies_to must be a sequence")

        effects = rule.get("effects")
        if not isinstance(effects, Mapping) or not effects:
            raise ValueError(f"{rule_id}: effects must not be empty")
        for profile_id, effect in effects.items():
            if profile_id not in HAZARD_PROFILES:
                raise ValueError(f"{rule_id}: unknown profile {profile_id}")
            if not isinstance(effect, Mapping):
                raise ValueError(f"{rule_id}: invalid effect for {profile_id}")
            severity = effect.get("severity")
            if severity not in SEVERITY_LEVELS or severity == 0:
                raise ValueError(f"{rule_id}: invalid nonzero severity")
            if not effect.get("impact"):
                raise ValueError(f"{rule_id}: effect requires an impact")
            if effect.get("traversability") not in {
                "passable",
                "passable_with_extreme_risk",
                "impassable",
            }:
                raise ValueError(f"{rule_id}: invalid traversability")


def ruleset_hash(rules: Sequence[Mapping[str, Any]]) -> str:
    encoded = json.dumps(
        list(rules),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def public_rule_metadata(
    rules: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Publish explanations and effects, never executable conditions."""

    return [
        {
            "id": rule["id"],
            "category": rule["category"],
            "description": rule["description"],
            "confidence": rule["confidence"],
            "directional": bool(rule.get("directional")),
            "effects": rule["effects"],
        }
        for rule in rules
    ]

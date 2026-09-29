"""Evaluate normalized pedestrian evidence against the hazard policy."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from accessibility.normalization import (
    is_unknown,
    normalize_categorical,
    parse_number,
    prepare_feature,
)

from .rules import HAZARD_CATEGORIES, HAZARD_PROFILES, HAZARD_RULES


def _condition_matches(
    condition: Mapping[str, Any], feature: Mapping[str, Any]
) -> bool:
    actual = feature.get(condition["field"])
    operator = condition["operator"]

    if operator == "transition_pair":
        if not isinstance(actual, Sequence) or isinstance(actual, str):
            return False
        return any(
            isinstance(state, Mapping)
            and normalize_categorical(state.get("kerb"))
            == normalize_categorical(condition.get("kerb"))
            and normalize_categorical(state.get("tactile_paving"))
            == normalize_categorical(condition.get("tactile_paving"))
            for state in actual
        )
    if operator == "equals":
        return normalize_categorical(actual) == normalize_categorical(
            condition.get("value")
        )
    if operator == "contains":
        if not isinstance(actual, Sequence) or isinstance(actual, str):
            return False
        expected = normalize_categorical(condition.get("value"))
        return expected in {normalize_categorical(item) for item in actual}
    if operator == "in":
        expected = {
            normalize_categorical(item) for item in condition.get("value", [])
        }
        return normalize_categorical(actual) in expected

    number = parse_number(actual)
    if number is None:
        return False
    if operator == "gt":
        return number > float(condition["value"])
    if operator == "gte":
        return number >= float(condition["value"])
    if operator == "lt":
        return number < float(condition["value"])
    if operator == "lte":
        return number <= float(condition["value"])
    if operator == "abs_gt":
        return abs(number) > float(condition["value"])
    if operator == "range":
        return (
            number > float(condition["min_exclusive"])
            and number <= float(condition["max_inclusive"])
        )
    if operator == "abs_range":
        magnitude = abs(number)
        return (
            magnitude > float(condition["min_exclusive"])
            and magnitude <= float(condition["max_inclusive"])
        )
    if operator == "negative_range":
        magnitude = abs(number)
        return (
            number < 0
            and magnitude > float(condition["min_abs_exclusive"])
            and magnitude <= float(condition["max_abs_inclusive"])
        )
    raise ValueError(f"unsupported hazard condition operator: {operator}")


def _coverage(feature: Mapping[str, Any]) -> int:
    evidence = [
        not is_unknown(feature.get("surface")),
        not is_unknown(feature.get("smoothness")),
        parse_number(feature.get("incline_percent")) is not None,
        parse_number(feature.get("cross_slope_percent")) is not None,
        not is_unknown(feature.get("wheelchair")),
    ]
    if feature.get("edge_kind") == "crossing":
        evidence.extend(
            [
                bool(feature.get("associated_kerbs")),
                bool(feature.get("associated_tactile_paving")),
                bool(feature.get("associated_transition_states")),
            ]
        )
    return round(sum(evidence) / len(evidence) * 100)


def _rule_confidence(
    rule: Mapping[str, Any], feature: Mapping[str, Any]
) -> int:
    confidence = int(rule["confidence"])
    if rule["category"] == "longitudinal_slope":
        confidence = min(
            confidence, int(feature.get("incline_confidence") or 0)
        )
    elif rule["category"] == "cross_slope":
        confidence = min(
            confidence, int(feature.get("cross_slope_confidence") or 0)
        )
    return confidence


def _direction_assessment(
    feature: Mapping[str, Any],
    profile_id: str,
    direction: str,
    rules: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    directional = dict(feature)
    incline = parse_number(feature.get("incline_percent"))
    directional["directional_incline_percent"] = (
        None
        if incline is None
        else incline if direction == "forward" else -incline
    )
    edge_kind = str(feature.get("edge_kind") or "footway")
    matches = []
    for rule in rules:
        if profile_id not in rule["effects"]:
            continue
        contexts = rule.get("applies_to", [])
        if contexts and edge_kind not in contexts:
            continue
        if _condition_matches(rule["condition"], directional):
            effect = dict(rule["effects"][profile_id])
            matches.append(
                {
                    "rule_id": rule["id"],
                    "category": rule["category"],
                    "description": rule["description"],
                    "confidence": _rule_confidence(rule, directional),
                    **effect,
                }
            )

    categories: dict[str, dict[str, Any]] = {}
    for category_id in HAZARD_CATEGORIES:
        category_matches = [
            match for match in matches if match["category"] == category_id
        ]
        severity = max(
            (int(match["severity"]) for match in category_matches), default=0
        )
        categories[category_id] = {
            "severity": severity,
            "rule_ids": [
                match["rule_id"]
                for match in category_matches
                if int(match["severity"]) == severity
            ],
        }

    severity = max((int(match["severity"]) for match in matches), default=0)
    decisive = [
        match for match in matches if int(match["severity"]) == severity
    ]
    traversability_order = {
        "passable": 0,
        "passable_with_extreme_risk": 1,
        "impassable": 2,
    }
    traversability = max(
        (match["traversability"] for match in decisive),
        default="passable",
        key=lambda value: traversability_order[value],
    )
    coverage = _coverage(feature)
    if severity:
        status = "hazard_detected"
    elif coverage >= 60:
        status = "no_detected_hazard"
    else:
        status = "insufficient_data"
    return {
        "severity": severity,
        "impact": sorted({match["impact"] for match in decisive}),
        "traversability": traversability,
        "confidence": max(
            (int(match["confidence"]) for match in decisive),
            default=coverage,
        ),
        "coverage": coverage,
        "status": status,
        "rule_ids": [match["rule_id"] for match in decisive],
        "categories": categories,
        "evidence": matches,
    }


def assess_feature(
    feature: Mapping[str, Any],
    *,
    normalized: bool = False,
    rules: Sequence[Mapping[str, Any]] = HAZARD_RULES,
) -> dict[str, Any]:
    prepared = dict(feature) if normalized else prepare_feature(feature)
    return {
        profile_id: {
            direction: _direction_assessment(
                prepared, profile_id, direction, rules
            )
            for direction in ("forward", "backward")
        }
        for profile_id in HAZARD_PROFILES
    }


def compact_hazard_properties(
    assessment: Mapping[str, Any], profile_id: str
) -> dict[str, Any]:
    directions = assessment[profile_id]
    forward = directions["forward"]
    backward = directions["backward"]
    worst = max(
        (forward, backward),
        key=lambda item: (
            int(item["severity"]),
            item["traversability"] == "impassable",
            int(item["confidence"]),
        ),
    )
    categories = {
        category_id: max(
            int(forward["categories"][category_id]["severity"]),
            int(backward["categories"][category_id]["severity"]),
        )
        for category_id in HAZARD_CATEGORIES
    }

    def compact_direction(item: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "severity": int(item["severity"]),
            "traversability": item["traversability"],
            "confidence": int(item["confidence"]),
            "coverage": int(item["coverage"]),
            "status": item["status"],
            "rule_ids": item["rule_ids"],
        }

    return {
        "severity": int(worst["severity"]),
        "severity_fwd": int(forward["severity"]),
        "severity_bwd": int(backward["severity"]),
        "impact": worst["impact"],
        "traversability": worst["traversability"],
        "confidence": int(worst["confidence"]),
        "coverage": int(worst["coverage"]),
        "status": worst["status"],
        "rule_ids": worst["rule_ids"],
        **{
            f"category_{category_id}": severity
            for category_id, severity in categories.items()
        },
        "forward": compact_direction(forward),
        "backward": compact_direction(backward),
    }

"""Generic interpreter for the human-editable routing profile dictionaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from statistics import fmean
from typing import Any

from accessibility.normalization import (
    is_unknown,
    normalize_categorical,
    parse_incline_percent,
    parse_number,
    parse_width_m,
    prepare_feature,
)

from .profile_rules import ROUTING_PROFILES
from .profile_validation import validate_profiles


def _context_applies(rule: Mapping[str, Any], edge_kind: str) -> bool:
    contexts = rule.get("applies_to", [])
    return not contexts or edge_kind in contexts


def _condition_matches(rule: Mapping[str, Any], feature: Mapping[str, Any]) -> bool:
    actual = feature.get(rule["field"])
    expected = rule["value"]
    operator = rule["operator"]

    if operator == "equals":
        return normalize_categorical(actual) == normalize_categorical(expected)
    if operator == "in":
        expected_values = {
            normalize_categorical(item) for item in expected
        }
        return normalize_categorical(actual) in expected_values
    if operator == "contains":
        if isinstance(actual, Sequence) and not isinstance(actual, str):
            expected = normalize_categorical(expected)
            return expected in {normalize_categorical(item) for item in actual}
        return False

    actual_number = parse_number(actual)
    expected_number = parse_number(expected)
    if actual_number is None or expected_number is None:
        return False
    return {
        "lt": actual_number < expected_number,
        "lte": actual_number <= expected_number,
        "gt": actual_number > expected_number,
        "gte": actual_number >= expected_number,
    }.get(operator, False)


def _grade_from_bands(value: float, bands: list[dict[str, Any]]) -> float:
    for band in bands:
        if band["max"] is None or value <= band["max"]:
            return float(band["grade"])
    raise RuntimeError("validated bands must have an open-ended final band")


def _categorical_grade(
    value: Any, rule: Mapping[str, Any]
) -> tuple[float, int]:
    values = value if isinstance(value, list) else [value]
    if not values:
        return float(rule["unknown_grade"]), 0

    grades = []
    confidences = []
    lookup = rule["values"]
    for item in values:
        normalized = normalize_categorical(item)
        if is_unknown(normalized):
            grades.append(float(rule["unknown_grade"]))
            confidences.append(0)
        elif normalized in lookup:
            grades.append(float(lookup[normalized]))
            confidences.append(100)
        else:
            grades.append(float(rule["unknown_grade"]))
            # A present but unmodelled value is more informative than absence,
            # while still signalling the rules need extension.
            confidences.append(25)

    aggregation = rule.get("aggregation", "minimum")
    if aggregation == "maximum":
        return max(grades), max(confidences)
    if aggregation == "mean":
        return fmean(grades), round(fmean(confidences))
    limiting_index = min(range(len(grades)), key=grades.__getitem__)
    return grades[limiting_index], confidences[limiting_index]


def _factor_grade(
    feature: Mapping[str, Any],
    rule: Mapping[str, Any],
    *,
    direction: str,
) -> tuple[float, int]:
    value = feature.get(rule["field"])
    factor_type = rule["type"]

    if factor_type == "categorical":
        return _categorical_grade(value, rule)

    if is_unknown(value):
        return float(rule["unknown_grade"]), 0
    number = parse_number(value)
    if number is None:
        return float(rule["unknown_grade"]), 0

    confidence = 100
    if rule["field"] == "incline_percent":
        confidence = int(feature.get("incline_confidence", 0))
    elif rule["field"] == "cross_slope_percent":
        confidence = int(feature.get("cross_slope_confidence", 0))

    if factor_type == "numeric_bands":
        if rule.get("absolute", False):
            number = abs(number)
        return _grade_from_bands(number, rule["bands"]), confidence

    directed_value = number if direction == "forward" else -number
    if directed_value >= 0:
        grade = _grade_from_bands(abs(directed_value), rule["ascending"])
    else:
        grade = _grade_from_bands(abs(directed_value), rule["descending"])
    return grade, confidence


def _weighted_harmonic_mean(items: list[tuple[float, float]]) -> float:
    if not items:
        return 100.0
    if any(grade <= 0 for grade, _weight in items):
        return 0.0
    total_weight = sum(weight for _grade, weight in items)
    return total_weight / sum(weight / grade for grade, weight in items)


def _weighted_confidence(items: list[tuple[int, float]]) -> int:
    if not items:
        return 0
    total_weight = sum(weight for _confidence, weight in items)
    return round(
        sum(confidence * weight for confidence, weight in items) / total_weight
    )


def _grade_direction(
    feature: Mapping[str, Any],
    profile: Mapping[str, Any],
    *,
    direction: str,
) -> dict[str, Any]:
    edge_kind = feature["edge_kind"]
    barrier_reasons = [
        rule["reason"]
        for rule in profile.get("barriers", [])
        if _context_applies(rule, edge_kind)
        and _condition_matches(rule, feature)
    ]
    if barrier_reasons:
        return {
            "grade": 0,
            "allowed": False,
            "confidence": 100,
            "reasons": barrier_reasons,
            "limiting_factor": "barrier",
        }

    factor_items: list[tuple[float, float]] = []
    confidence_items: list[tuple[int, float]] = []
    factor_details: dict[str, float] = {}
    for factor_id, rule in profile["factors"].items():
        if not _context_applies(rule, edge_kind):
            continue
        grade, confidence = _factor_grade(feature, rule, direction=direction)
        weight = float(rule["factor_weight"])
        factor_items.append((grade, weight))
        confidence_items.append((confidence, weight))
        factor_details[factor_id] = grade

    grade = _weighted_harmonic_mean(factor_items)
    reasons = []
    for rule in profile.get("grade_caps", []):
        if (
            _context_applies(rule, edge_kind)
            and _condition_matches(rule, feature)
            and grade > rule["max_grade"]
        ):
            grade = float(rule["max_grade"])
            reasons.append(rule["reason"])

    limiting_factor = (
        min(factor_details, key=factor_details.get) if factor_details else None
    )
    if limiting_factor and factor_details[limiting_factor] < 50:
        reasons.append(limiting_factor)

    return {
        "grade": max(0, min(100, round(grade))),
        "allowed": grade > 0,
        "confidence": _weighted_confidence(confidence_items),
        "reasons": list(dict.fromkeys(reasons)),
        "limiting_factor": limiting_factor,
    }


def grade_feature(
    feature: Mapping[str, Any],
    *,
    edge_kind: str | None = None,
    estimated_slope_percent: float | None = None,
    slope_source: str = "missing",
    slope_confidence: int = 0,
    profiles: Mapping[str, Any] = ROUTING_PROFILES,
) -> dict[str, Any]:
    """Grade a feature in both coordinate directions for every profile."""

    validate_profiles(profiles)
    prepared = prepare_feature(
        feature,
        edge_kind=edge_kind,
        estimated_slope_percent=estimated_slope_percent,
        slope_source=slope_source,
        slope_confidence=slope_confidence,
    )
    result = {
        "prepared": prepared,
        "profiles": {},
    }
    for profile_id, profile in profiles.items():
        if profile["routing_mode"] == "distance":
            continue
        result["profiles"][profile_id] = {
            "forward": _grade_direction(
                prepared, profile, direction="forward"
            ),
            "backward": _grade_direction(
                prepared, profile, direction="backward"
            ),
        }
    return result


def compact_grade_properties(graded: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten grading results into compact GeoJSON-safe edge properties."""

    properties: dict[str, Any] = {}
    for profile_id, result in graded["profiles"].items():
        forward = result["forward"]
        backward = result["backward"]
        properties[f"{profile_id}_grade_fwd"] = int(forward["grade"])
        properties[f"{profile_id}_grade_bwd"] = int(backward["grade"])
        properties[f"{profile_id}_allow_fwd"] = bool(forward["allowed"])
        properties[f"{profile_id}_allow_bwd"] = bool(backward["allowed"])
        properties[f"{profile_id}_confidence"] = min(
            int(forward["confidence"]), int(backward["confidence"])
        )
        limiting_direction = (
            forward
            if forward["grade"] <= backward["grade"]
            else backward
        )
        limiting = limiting_direction.get("limiting_factor")
        if limiting:
            properties[f"{profile_id}_limit"] = limiting
    return properties

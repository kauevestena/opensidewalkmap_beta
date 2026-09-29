"""Validation and serialization helpers for routing profile dictionaries."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


SUPPORTED_FACTOR_TYPES = {
    "categorical",
    "numeric_bands",
    "directional_numeric_bands",
}
SUPPORTED_OPERATORS = {"equals", "in", "contains", "lt", "lte", "gt", "gte"}
SUPPORTED_ROUTING_MODES = {"accessibility_grade", "distance"}
KNOWN_EDGE_KINDS = {"sidewalk", "footway", "crossing", "stairs"}


class ProfileValidationError(ValueError):
    """Raised when the human-editable profile rules are inconsistent."""


def _check_grade(value: Any, location: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProfileValidationError(f"{location} must be numeric")
    if not 0 <= value <= 100:
        raise ProfileValidationError(f"{location} must be between 0 and 100")


def _validate_bands(bands: Any, location: str) -> None:
    if not isinstance(bands, list) or not bands:
        raise ProfileValidationError(f"{location} must be a non-empty list")

    previous = float("-inf")
    saw_open_end = False
    for index, band in enumerate(bands):
        here = f"{location}[{index}]"
        if not isinstance(band, Mapping):
            raise ProfileValidationError(f"{here} must be a dictionary")
        if set(band) != {"max", "grade"}:
            raise ProfileValidationError(
                f"{here} must contain exactly 'max' and 'grade'"
            )
        _check_grade(band["grade"], f"{here}.grade")
        maximum = band["max"]
        if maximum is None:
            if index != len(bands) - 1:
                raise ProfileValidationError(
                    f"{here}.max=None is only valid for the last band"
                )
            saw_open_end = True
            continue
        if not isinstance(maximum, (int, float)) or isinstance(maximum, bool):
            raise ProfileValidationError(f"{here}.max must be numeric or None")
        if maximum <= previous:
            raise ProfileValidationError(f"{location} maxima must be increasing")
        previous = maximum

    if not saw_open_end:
        raise ProfileValidationError(f"{location} must end with max=None")


def _validate_factor(profile_id: str, factor_id: str, rule: Any) -> None:
    location = f"{profile_id}.factors.{factor_id}"
    if not isinstance(rule, Mapping):
        raise ProfileValidationError(f"{location} must be a dictionary")

    factor_type = rule.get("type")
    if factor_type not in SUPPORTED_FACTOR_TYPES:
        raise ProfileValidationError(
            f"{location}.type must be one of {sorted(SUPPORTED_FACTOR_TYPES)}"
        )
    if not isinstance(rule.get("field"), str) or not rule["field"]:
        raise ProfileValidationError(f"{location}.field must be a non-empty string")

    weight = rule.get("factor_weight")
    if (
        not isinstance(weight, (int, float))
        or isinstance(weight, bool)
        or weight <= 0
    ):
        raise ProfileValidationError(f"{location}.factor_weight must be positive")
    _check_grade(rule.get("unknown_grade"), f"{location}.unknown_grade")

    contexts = rule.get("applies_to", [])
    if not isinstance(contexts, list) or any(
        context not in KNOWN_EDGE_KINDS for context in contexts
    ):
        raise ProfileValidationError(
            f"{location}.applies_to contains an unknown edge kind"
        )

    if rule.get("aggregation", "minimum") not in {"minimum", "maximum", "mean"}:
        raise ProfileValidationError(f"{location}.aggregation is unsupported")

    if factor_type == "categorical":
        values = rule.get("values")
        if not isinstance(values, Mapping) or not values:
            raise ProfileValidationError(f"{location}.values must not be empty")
        for value, grade in values.items():
            if not isinstance(value, str):
                raise ProfileValidationError(
                    f"{location}.values keys must be strings"
                )
            _check_grade(grade, f"{location}.values[{value!r}]")
    elif factor_type == "numeric_bands":
        _validate_bands(rule.get("bands"), f"{location}.bands")
    else:
        _validate_bands(rule.get("ascending"), f"{location}.ascending")
        _validate_bands(rule.get("descending"), f"{location}.descending")


def _validate_condition(profile_id: str, group: str, index: int, rule: Any) -> None:
    location = f"{profile_id}.{group}[{index}]"
    if not isinstance(rule, Mapping):
        raise ProfileValidationError(f"{location} must be a dictionary")
    if not isinstance(rule.get("field"), str) or not rule["field"]:
        raise ProfileValidationError(f"{location}.field must be a non-empty string")
    if rule.get("operator") not in SUPPORTED_OPERATORS:
        raise ProfileValidationError(f"{location}.operator is unsupported")
    if "value" not in rule:
        raise ProfileValidationError(f"{location}.value is required")
    if not isinstance(rule.get("reason"), str) or not rule["reason"]:
        raise ProfileValidationError(f"{location}.reason is required")

    contexts = rule.get("applies_to", [])
    if not isinstance(contexts, list) or any(
        context not in KNOWN_EDGE_KINDS for context in contexts
    ):
        raise ProfileValidationError(
            f"{location}.applies_to contains an unknown edge kind"
        )

    if group == "grade_caps":
        _check_grade(rule.get("max_grade"), f"{location}.max_grade")


def _validate_cost(profile_id: str, cost: Any) -> None:
    location = f"{profile_id}.cost"
    if not isinstance(cost, Mapping):
        raise ProfileValidationError(f"{location} must be a dictionary")

    multipliers = cost.get("grade_multipliers")
    if not isinstance(multipliers, list) or not multipliers:
        raise ProfileValidationError(
            f"{location}.grade_multipliers must be a non-empty list"
        )

    previous_grade = 101
    previous_multiplier = 0.0
    for index, item in enumerate(multipliers):
        here = f"{location}.grade_multipliers[{index}]"
        if not isinstance(item, Mapping) or set(item) != {
            "min_grade",
            "multiplier",
        }:
            raise ProfileValidationError(
                f"{here} must contain min_grade and multiplier"
            )
        min_grade = item["min_grade"]
        multiplier = item["multiplier"]
        _check_grade(min_grade, f"{here}.min_grade")
        if min_grade >= previous_grade:
            raise ProfileValidationError(
                f"{location}.grade_multipliers must descend by min_grade"
            )
        if (
            not isinstance(multiplier, (int, float))
            or isinstance(multiplier, bool)
            or multiplier <= 0
        ):
            raise ProfileValidationError(f"{here}.multiplier must be positive")
        if multiplier < previous_multiplier:
            raise ProfileValidationError(
                f"{location} multipliers must not decrease as grades worsen"
            )
        previous_grade = min_grade
        previous_multiplier = multiplier

    penalties = cost.get("event_penalties_m")
    if not isinstance(penalties, Mapping):
        raise ProfileValidationError(
            f"{location}.event_penalties_m must be a dictionary"
        )
    if set(penalties) != KNOWN_EDGE_KINDS:
        raise ProfileValidationError(
            f"{location}.event_penalties_m must cover {sorted(KNOWN_EDGE_KINDS)}"
        )
    for edge_kind, penalty in penalties.items():
        if penalty is not None and (
            not isinstance(penalty, (int, float))
            or isinstance(penalty, bool)
            or penalty < 0
        ):
            raise ProfileValidationError(
                f"{location}.event_penalties_m[{edge_kind!r}] "
                "must be non-negative or None"
            )


def validate_profiles(profiles: Mapping[str, Any]) -> None:
    """Validate profiles, raising :class:`ProfileValidationError` on failure."""

    if not isinstance(profiles, Mapping) or not profiles:
        raise ProfileValidationError("profiles must be a non-empty dictionary")

    distance_profile_ids = []
    for profile_id, profile in profiles.items():
        if not isinstance(profile_id, str) or not profile_id:
            raise ProfileValidationError("profile identifiers must be strings")
        if not isinstance(profile, Mapping):
            raise ProfileValidationError(f"{profile_id} must be a dictionary")
        for required in ("label", "description", "routing_mode", "speed_kmh"):
            if required not in profile:
                raise ProfileValidationError(f"{profile_id}.{required} is required")
        if not isinstance(profile["label"], str) or not profile["label"]:
            raise ProfileValidationError(f"{profile_id}.label must not be empty")
        if not isinstance(profile["description"], str):
            raise ProfileValidationError(f"{profile_id}.description must be text")
        routing_mode = profile["routing_mode"]
        if routing_mode not in SUPPORTED_ROUTING_MODES:
            raise ProfileValidationError(
                f"{profile_id}.routing_mode must be one of "
                f"{sorted(SUPPORTED_ROUTING_MODES)}"
            )
        if (
            isinstance(profile["speed_kmh"], bool)
            or not isinstance(profile["speed_kmh"], (int, float))
            or profile["speed_kmh"] <= 0
        ):
            raise ProfileValidationError(f"{profile_id}.speed_kmh must be positive")

        if routing_mode == "distance":
            distance_profile_ids.append(profile_id)
            redundant = {
                key
                for key in ("factors", "barriers", "grade_caps", "cost")
                if key in profile
            }
            if redundant:
                raise ProfileValidationError(
                    f"{profile_id} distance profile must not define "
                    f"{sorted(redundant)}"
                )
            continue

        for required in ("factors", "cost"):
            if required not in profile:
                raise ProfileValidationError(f"{profile_id}.{required} is required")
        factors = profile["factors"]
        if not isinstance(factors, Mapping) or not factors:
            raise ProfileValidationError(f"{profile_id}.factors must not be empty")
        for factor_id, factor in factors.items():
            _validate_factor(profile_id, factor_id, factor)

        for group in ("barriers", "grade_caps"):
            rules = profile.get(group, [])
            if not isinstance(rules, list):
                raise ProfileValidationError(f"{profile_id}.{group} must be a list")
            for index, rule in enumerate(rules):
                _validate_condition(profile_id, group, index, rule)

        _validate_cost(profile_id, profile["cost"])

    if len(distance_profile_ids) != 1:
        raise ProfileValidationError(
            "profiles must contain exactly one distance routing profile"
        )

    # This also verifies that the dictionaries contain no Python-only values.
    json.dumps(profiles, sort_keys=True, allow_nan=False)


def profile_ruleset_hash(profiles: Mapping[str, Any]) -> str:
    """Return a deterministic short hash for a validated ruleset."""

    validate_profiles(profiles)
    payload = json.dumps(
        profiles, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def public_profile_metadata(profiles: Mapping[str, Any]) -> dict[str, Any]:
    """Return the subset needed by the static JavaScript routing client."""

    validate_profiles(profiles)
    result = {}
    for profile_id, profile in profiles.items():
        metadata = {
            "label": profile["label"],
            "description": profile["description"],
            "routing_mode": profile["routing_mode"],
            "provisional": bool(profile.get("provisional", False)),
            "speed_kmh": profile["speed_kmh"],
        }
        if profile["routing_mode"] == "accessibility_grade":
            metadata["property_prefix"] = profile_id
            metadata["cost"] = profile["cost"]
        result[profile_id] = metadata
    return result

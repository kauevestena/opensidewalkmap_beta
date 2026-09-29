"""Human-editable pedestrian hazard policy.

These rules are deliberately provisional. Severity is not a probability and
must never be interpreted as proof that an unflagged feature is safe.
"""

from __future__ import annotations


HAZARD_RULESET_VERSION = "0.1.0"

SEVERITY_LEVELS = {
    0: {
        "label": "No detected hazard",
        "description": "No rule matched the available evidence.",
        "color": "#ffffff",
    },
    1: {
        "label": "Uncomfortable",
        "color": "#fee08b",
        "description": "May reduce comfort or require additional effort.",
    },
    2: {
        "label": "Unfavorable",
        "color": "#fdae61",
        "description": "Meaningfully degrades pedestrian accessibility.",
    },
    3: {
        "label": "Dangerous",
        "color": "#f46d43",
        "description": "May create a serious safety or mobility hazard.",
    },
    4: {
        "label": "Critical",
        "color": "#a50026",
        "description": "Potential barrier or extreme contextual safety risk.",
    },
}

HAZARD_CATEGORIES = {
    "longitudinal_slope": {
        "label": "Longitudinal slope",
        "description": "Directional terrain or explicitly mapped incline.",
    },
    "cross_slope": {
        "label": "Cross slope",
        "description": "Only explicit OSM incline:across evidence.",
    },
    "kerb": {
        "label": "Kerb transition",
        "description": "Kerb height/type and transition traversability.",
    },
    "tactile_orientation": {
        "label": "Tactile and orientation",
        "description": "Tactile evidence and detectable material transitions.",
    },
    "surface": {
        "label": "Surface",
        "description": "Smoothness plus provisional surface-material proxies.",
    },
    "barrier": {
        "label": "Barrier",
        "description": "Explicit or strongly inferred traversal barriers.",
    },
}

HAZARD_PROFILES = {
    "pedestrian": {
        "label": "Pedestrian",
        "description": "General walking comfort and safety.",
    },
    "wheelchair": {
        "label": "Wheelchair user",
        "description": "Continuous rollable access with manageable gradients.",
    },
    "blind": {
        "label": "Blind or low-vision pedestrian",
        "description": "Detectable, orientable and predictable transitions.",
    },
    "elderly": {
        "label": "Older or reduced-mobility pedestrian",
        "description": "Stability, effort and fall-risk oriented assessment.",
    },
}


def _effect(
    severity: int,
    impact: str,
    traversability: str = "passable",
) -> dict[str, object]:
    return {
        "severity": severity,
        "impact": impact,
        "traversability": traversability,
    }


HAZARD_RULES = [
    {
        "id": "barrier_steps",
        "category": "barrier",
        "description": "Steps interrupt step-free movement.",
        "confidence": 95,
        "condition": {"field": "highway", "operator": "equals", "value": "steps"},
        "effects": {
            "pedestrian": _effect(1, "Additional effort"),
            "wheelchair": _effect(4, "Step-free passage blocked", "impassable"),
            "blind": _effect(2, "Level change requires care"),
            "elderly": _effect(3, "High effort and fall risk"),
        },
    },
    {
        "id": "barrier_wheelchair_no",
        "category": "barrier",
        "description": "OSM explicitly marks wheelchair access as unavailable.",
        "confidence": 95,
        "condition": {"field": "wheelchair", "operator": "equals", "value": "no"},
        "effects": {
            "wheelchair": _effect(4, "Wheelchair access explicitly blocked", "impassable")
        },
    },
    {
        "id": "surface_impassable",
        "category": "barrier",
        "description": "OSM explicitly describes the surface as impassable.",
        "confidence": 95,
        "condition": {
            "field": "smoothness",
            "operator": "equals",
            "value": "impassable",
        },
        "effects": {
            "pedestrian": _effect(4, "Passage explicitly impassable", "impassable"),
            "wheelchair": _effect(4, "Passage explicitly impassable", "impassable"),
            "blind": _effect(4, "Passage explicitly impassable", "impassable"),
            "elderly": _effect(4, "Passage explicitly impassable", "impassable"),
        },
    },
    {
        "id": "kerb_raised",
        "category": "kerb",
        "description": "A raised kerb is associated with the crossing.",
        "confidence": 90,
        "applies_to": ["crossing"],
        "condition": {
            "field": "associated_kerbs",
            "operator": "contains",
            "value": "raised",
        },
        "effects": {
            "pedestrian": _effect(1, "Abrupt level change"),
            "wheelchair": _effect(4, "Kerb blocks independent passage", "impassable"),
            "elderly": _effect(3, "Trip and fall hazard"),
        },
    },
    {
        "id": "kerb_ambiguous_yes",
        "category": "kerb",
        "description": "A kerb is mapped without a traversable kerb type.",
        "confidence": 70,
        "applies_to": ["crossing"],
        "condition": {
            "field": "associated_kerbs",
            "operator": "contains",
            "value": "yes",
        },
        "effects": {
            "wheelchair": _effect(3, "Kerb traversability uncertain"),
            "elderly": _effect(2, "Potential abrupt level change"),
        },
    },
    {
        "id": "kerb_rolled",
        "category": "kerb",
        "description": "A rolled kerb can still require substantial effort.",
        "confidence": 85,
        "applies_to": ["crossing"],
        "condition": {
            "field": "associated_kerbs",
            "operator": "contains",
            "value": "rolled",
        },
        "effects": {
            "wheelchair": _effect(2, "Difficult rolling transition"),
            "blind": _effect(1, "Weakly defined transition"),
            "elderly": _effect(2, "Unstable transition"),
        },
    },
    {
        "id": "flush_without_tactile",
        "category": "tactile_orientation",
        "description": "A flush kerb is explicitly paired with absent tactile paving.",
        "confidence": 95,
        "applies_to": ["crossing"],
        "condition": {
            "field": "associated_transition_states",
            "operator": "transition_pair",
            "kerb": "flush",
            "tactile_paving": "no",
        },
        "effects": {
            "blind": _effect(
                4,
                "Street boundary may be undetectable",
                "passable_with_extreme_risk",
            ),
            "elderly": _effect(1, "Transition lacks tactile cue"),
        },
    },
    {
        "id": "lowered_without_tactile",
        "category": "tactile_orientation",
        "description": "A lowered kerb is explicitly paired with absent tactile paving.",
        "confidence": 90,
        "applies_to": ["crossing"],
        "condition": {
            "field": "associated_transition_states",
            "operator": "transition_pair",
            "kerb": "lowered",
            "tactile_paving": "no",
        },
        "effects": {
            "blind": _effect(3, "Street boundary has weak tactile detection"),
        },
    },
    {
        "id": "crossing_tactile_no",
        "category": "tactile_orientation",
        "description": "Tactile paving is explicitly absent at the crossing.",
        "confidence": 90,
        "applies_to": ["crossing"],
        "condition": {
            "field": "associated_tactile_paving",
            "operator": "contains",
            "value": "no",
        },
        "effects": {
            "blind": _effect(3, "No mapped tactile warning at street transition"),
        },
    },
    {
        "id": "uniform_transition_surface",
        "category": "tactile_orientation",
        "description": (
            "Crossing, kerb and adjacent sidewalk share one explicitly mapped "
            "surface; this is a low-confidence detectability proxy."
        ),
        "confidence": 45,
        "applies_to": ["crossing"],
        "condition": {
            "field": "uniform_transition_surface",
            "operator": "equals",
            "value": True,
        },
        "effects": {
            "blind": _effect(3, "Material transition may be difficult to detect"),
        },
    },
    {
        "id": "smoothness_very_horrible",
        "category": "surface",
        "description": "Very horrible smoothness indicates an extreme unevenness.",
        "confidence": 90,
        "condition": {
            "field": "smoothness",
            "operator": "equals",
            "value": "very_horrible",
        },
        "effects": {
            "pedestrian": _effect(3, "Extreme unevenness"),
            "wheelchair": _effect(4, "Independent rolling may be impossible", "impassable"),
            "blind": _effect(3, "Severe trip and orientation hazard"),
            "elderly": _effect(4, "Extreme fall risk", "passable_with_extreme_risk"),
        },
    },
    {
        "id": "smoothness_horrible",
        "category": "surface",
        "description": "Horrible smoothness indicates severe unevenness.",
        "confidence": 90,
        "condition": {
            "field": "smoothness",
            "operator": "equals",
            "value": "horrible",
        },
        "effects": {
            "pedestrian": _effect(2, "Severe unevenness"),
            "wheelchair": _effect(4, "Rolling may be effectively blocked", "impassable"),
            "blind": _effect(3, "Severe trip hazard"),
            "elderly": _effect(3, "High fall risk"),
        },
    },
    {
        "id": "smoothness_very_bad",
        "category": "surface",
        "description": "Very bad smoothness creates substantial mobility difficulty.",
        "confidence": 90,
        "condition": {
            "field": "smoothness",
            "operator": "equals",
            "value": "very_bad",
        },
        "effects": {
            "pedestrian": _effect(2, "Substantial unevenness"),
            "wheelchair": _effect(3, "Very difficult rolling surface"),
            "blind": _effect(2, "Substantial trip hazard"),
            "elderly": _effect(3, "High instability"),
        },
    },
    {
        "id": "smoothness_bad",
        "category": "surface",
        "description": "Bad smoothness creates a meaningful mobility penalty.",
        "confidence": 90,
        "condition": {
            "field": "smoothness",
            "operator": "equals",
            "value": "bad",
        },
        "effects": {
            "pedestrian": _effect(1, "Uneven walking surface"),
            "wheelchair": _effect(2, "Difficult rolling surface"),
            "blind": _effect(2, "Trip hazard"),
            "elderly": _effect(2, "Instability and fall risk"),
        },
    },
    {
        "id": "surface_sand",
        "category": "surface",
        "description": "Surface material is a provisional mobility proxy.",
        "confidence": 55,
        "condition": {"field": "surface", "operator": "equals", "value": "sand"},
        "effects": {
            "pedestrian": _effect(2, "Loose surface"),
            "wheelchair": _effect(4, "Wheels may become immobilized", "impassable"),
            "blind": _effect(2, "Unstable surface"),
            "elderly": _effect(3, "High instability"),
        },
    },
    {
        "id": "surface_grass",
        "category": "surface",
        "description": "Surface material is a provisional mobility proxy.",
        "confidence": 55,
        "condition": {"field": "surface", "operator": "equals", "value": "grass"},
        "effects": {
            "pedestrian": _effect(1, "Variable natural surface"),
            "wheelchair": _effect(3, "High rolling resistance"),
            "blind": _effect(1, "Variable surface"),
            "elderly": _effect(2, "Unstable footing"),
        },
    },
    {
        "id": "surface_ground_earth_dirt",
        "category": "surface",
        "description": "Surface material is a provisional mobility proxy.",
        "confidence": 55,
        "condition": {
            "field": "surface",
            "operator": "in",
            "value": ["ground", "earth", "dirt", "unpaved"],
        },
        "effects": {
            "pedestrian": _effect(1, "Weather-sensitive surface"),
            "wheelchair": _effect(3, "High or variable rolling resistance"),
            "blind": _effect(1, "Irregular surface"),
            "elderly": _effect(2, "Unstable footing"),
        },
    },
    {
        "id": "surface_gravel",
        "category": "surface",
        "description": "Surface material is a provisional mobility proxy.",
        "confidence": 55,
        "condition": {"field": "surface", "operator": "equals", "value": "gravel"},
        "effects": {
            "pedestrian": _effect(1, "Loose aggregate"),
            "wheelchair": _effect(3, "Difficult rolling surface"),
            "blind": _effect(1, "Loose aggregate"),
            "elderly": _effect(2, "Unstable footing"),
        },
    },
    {
        "id": "surface_cobble_sett",
        "category": "surface",
        "description": "Surface material is a provisional mobility proxy.",
        "confidence": 55,
        "condition": {
            "field": "surface",
            "operator": "in",
            "value": ["cobblestone", "unhewn_cobblestone", "sett"],
        },
        "effects": {
            "pedestrian": _effect(1, "Uneven joints"),
            "wheelchair": _effect(3, "Difficult vibration-heavy rolling"),
            "blind": _effect(2, "Irregular trip-prone surface"),
            "elderly": _effect(2, "Trip and instability hazard"),
        },
    },
    {
        "id": "surface_compacted_fine_gravel",
        "category": "surface",
        "description": "Surface material is a provisional mobility proxy.",
        "confidence": 50,
        "condition": {
            "field": "surface",
            "operator": "in",
            "value": ["compacted", "fine_gravel"],
        },
        "effects": {
            "wheelchair": _effect(2, "Increased rolling resistance"),
            "elderly": _effect(1, "Potentially loose footing"),
        },
    },
    {
        "id": "cross_slope_over_5",
        "category": "cross_slope",
        "description": "Explicit cross slope exceeds 5%.",
        "confidence": 95,
        "condition": {
            "field": "cross_slope_percent",
            "operator": "abs_gt",
            "value": 5,
        },
        "effects": {
            "pedestrian": _effect(2, "Strong lateral imbalance"),
            "wheelchair": _effect(4, "High tip or drift risk", "passable_with_extreme_risk"),
            "blind": _effect(2, "Strong lateral imbalance"),
            "elderly": _effect(3, "High fall risk"),
        },
    },
    {
        "id": "cross_slope_3_to_5",
        "category": "cross_slope",
        "description": "Explicit cross slope is greater than 3% and at most 5%.",
        "confidence": 95,
        "condition": {
            "field": "cross_slope_percent",
            "operator": "abs_range",
            "min_exclusive": 3,
            "max_inclusive": 5,
        },
        "effects": {
            "pedestrian": _effect(1, "Lateral imbalance"),
            "wheelchair": _effect(3, "Substantial drift or tip risk"),
            "blind": _effect(1, "Lateral imbalance"),
            "elderly": _effect(2, "Instability"),
        },
    },
    {
        "id": "cross_slope_2_to_3",
        "category": "cross_slope",
        "description": "Explicit cross slope is greater than 2% and at most 3%.",
        "confidence": 95,
        "condition": {
            "field": "cross_slope_percent",
            "operator": "abs_range",
            "min_exclusive": 2,
            "max_inclusive": 3,
        },
        "effects": {
            "wheelchair": _effect(2, "Noticeable lateral effort"),
            "elderly": _effect(1, "Mild lateral instability"),
        },
    },
    {
        "id": "uphill_over_12_5",
        "category": "longitudinal_slope",
        "description": "Travel direction rises by more than 12.5%.",
        "confidence": 80,
        "directional": True,
        "condition": {
            "field": "directional_incline_percent",
            "operator": "gt",
            "value": 12.5,
        },
        "effects": {
            "pedestrian": _effect(3, "Extreme climbing effort"),
            "wheelchair": _effect(4, "Independent ascent may be impossible", "impassable"),
            "blind": _effect(2, "Extreme climbing effort"),
            "elderly": _effect(4, "Extreme exertion and fall risk", "passable_with_extreme_risk"),
        },
    },
    {
        "id": "uphill_8_33_to_12_5",
        "category": "longitudinal_slope",
        "description": "Travel direction rises by more than 8.33% and at most 12.5%.",
        "confidence": 80,
        "directional": True,
        "condition": {
            "field": "directional_incline_percent",
            "operator": "range",
            "min_exclusive": 8.33,
            "max_inclusive": 12.5,
        },
        "effects": {
            "pedestrian": _effect(2, "High climbing effort"),
            "wheelchair": _effect(3, "Very difficult ascent"),
            "blind": _effect(1, "High climbing effort"),
            "elderly": _effect(3, "High exertion"),
        },
    },
    {
        "id": "uphill_5_to_8_33",
        "category": "longitudinal_slope",
        "description": "Travel direction rises by more than 5% and at most 8.33%.",
        "confidence": 80,
        "directional": True,
        "condition": {
            "field": "directional_incline_percent",
            "operator": "range",
            "min_exclusive": 5,
            "max_inclusive": 8.33,
        },
        "effects": {
            "pedestrian": _effect(1, "Increased climbing effort"),
            "wheelchair": _effect(2, "Difficult ascent"),
            "elderly": _effect(2, "Increased exertion"),
        },
    },
    {
        "id": "downhill_over_12_5",
        "category": "longitudinal_slope",
        "description": "Travel direction descends by more than 12.5%.",
        "confidence": 80,
        "directional": True,
        "condition": {
            "field": "directional_incline_percent",
            "operator": "lt",
            "value": -12.5,
        },
        "effects": {
            "pedestrian": _effect(3, "Extreme braking and fall risk"),
            "wheelchair": _effect(4, "Loss-of-control risk", "passable_with_extreme_risk"),
            "blind": _effect(3, "Extreme descent hazard"),
            "elderly": _effect(4, "Extreme fall risk", "passable_with_extreme_risk"),
        },
    },
    {
        "id": "downhill_8_33_to_12_5",
        "category": "longitudinal_slope",
        "description": "Travel direction descends by more than 8.33% and at most 12.5%.",
        "confidence": 80,
        "directional": True,
        "condition": {
            "field": "directional_incline_percent",
            "operator": "negative_range",
            "min_abs_exclusive": 8.33,
            "max_abs_inclusive": 12.5,
        },
        "effects": {
            "pedestrian": _effect(2, "High braking effort"),
            "wheelchair": _effect(3, "Substantial loss-of-control risk"),
            "blind": _effect(2, "Steep descent hazard"),
            "elderly": _effect(3, "High fall risk"),
        },
    },
    {
        "id": "downhill_5_to_8_33",
        "category": "longitudinal_slope",
        "description": "Travel direction descends by more than 5% and at most 8.33%.",
        "confidence": 80,
        "directional": True,
        "condition": {
            "field": "directional_incline_percent",
            "operator": "negative_range",
            "min_abs_exclusive": 5,
            "max_abs_inclusive": 8.33,
        },
        "effects": {
            "pedestrian": _effect(1, "Increased braking effort"),
            "wheelchair": _effect(2, "Difficult controlled descent"),
            "blind": _effect(1, "Increased descent care"),
            "elderly": _effect(2, "Increased fall risk"),
        },
    },
]

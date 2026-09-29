"""Human-editable accessibility profile rules.

This file is the policy surface of OSWM routing.  Values in this module are
plain Python dictionaries on purpose: they should be readable and adjustable
without changing the grading engine.

Grades always range from 0 (unusable) to 100 (excellent). ``factor_weight``
expresses the relative importance of a factor inside a profile; it is not a
routing edge cost.  Hard barriers and grade caps are declared separately so a
very good value cannot accidentally compensate for an impassable condition.

The accessibility values are deliberately marked provisional. They recover
useful ordering from OSWM's historical accessibility experiment, correct
obvious old errors, and provide a testable starting point for calibration with
users and accessibility specialists. The distance-only profile is a neutral
baseline and does not generate redundant per-edge grades.
"""

PROFILE_RULESET_VERSION = "1.1.0"


ROUTING_PROFILES = {
    "distance": {
        "label": "Shortest distance",
        "description": (
            "Minimizes geometric walking distance without applying "
            "accessibility grades, barriers or event penalties."
        ),
        "routing_mode": "distance",
        "provisional": False,
        "speed_kmh": 5.0,
    },
    "wheelchair": {
        "label": "Wheelchair",
        "description": (
            "Prioritizes continuous, smooth, sufficiently wide routes with "
            "manageable longitudinal and cross slopes."
        ),
        "routing_mode": "accessibility_grade",
        "provisional": True,
        "speed_kmh": 3.5,
        "factors": {
            "surface": {
                "type": "categorical",
                "field": "surface",
                "factor_weight": 3.0,
                "unknown_grade": 35,
                "values": {
                    "asphalt": 100,
                    "concrete": 100,
                    "metal": 75,
                    "paving_stones": 82,
                    "paver": 82,
                    "concrete:plates": 72,
                    "ceramic:tiles": 70,
                    "compacted": 60,
                    "fine_gravel": 45,
                    "sett": 35,
                    "cobblestone": 30,
                    "unhewn_cobblestone": 20,
                    "gravel": 25,
                    "wood": 45,
                    "ground": 25,
                    "earth": 20,
                    "dirt": 20,
                    "grass": 15,
                    "sand": 5,
                    "unpaved": 20,
                    "paved": 65,
                },
            },
            "smoothness": {
                "type": "categorical",
                "field": "smoothness",
                "factor_weight": 5.0,
                "unknown_grade": 35,
                "values": {
                    "excellent": 100,
                    "good": 90,
                    "intermediate": 70,
                    "bad": 45,
                    "very_bad": 30,
                    "horrible": 15,
                    "very_horrible": 5,
                    "impassable": 0,
                },
            },
            "width": {
                "type": "numeric_bands",
                "field": "width_m",
                "factor_weight": 5.0,
                "unknown_grade": 35,
                "bands": [
                    {"max": 0.60, "grade": 0},
                    {"max": 0.90, "grade": 20},
                    {"max": 1.20, "grade": 60},
                    {"max": 1.50, "grade": 85},
                    {"max": None, "grade": 100},
                ],
            },
            "incline": {
                "type": "directional_numeric_bands",
                "field": "incline_percent",
                "factor_weight": 5.0,
                "unknown_grade": 40,
                "ascending": [
                    {"max": 2.0, "grade": 100},
                    {"max": 5.0, "grade": 82},
                    {"max": 8.33, "grade": 52},
                    {"max": 12.5, "grade": 20},
                    {"max": None, "grade": 0},
                ],
                "descending": [
                    {"max": 2.0, "grade": 100},
                    {"max": 5.0, "grade": 88},
                    {"max": 8.33, "grade": 62},
                    {"max": 12.5, "grade": 30},
                    {"max": None, "grade": 0},
                ],
            },
            "cross_slope": {
                "type": "numeric_bands",
                "field": "cross_slope_percent",
                "absolute": True,
                "factor_weight": 4.0,
                "unknown_grade": 40,
                "bands": [
                    {"max": 2.0, "grade": 100},
                    {"max": 3.0, "grade": 70},
                    {"max": 5.0, "grade": 35},
                    {"max": None, "grade": 5},
                ],
            },
            "wheelchair_tag": {
                "type": "categorical",
                "field": "wheelchair",
                "factor_weight": 2.0,
                "unknown_grade": 50,
                "values": {
                    "yes": 100,
                    "designated": 100,
                    "limited": 60,
                    "no": 0,
                },
            },
            "crossing": {
                "type": "categorical",
                "field": "crossing",
                "applies_to": ["crossing"],
                "factor_weight": 3.0,
                "unknown_grade": 45,
                "values": {
                    "traffic_signals": 90,
                    "zebra": 85,
                    "marked": 80,
                    "uncontrolled": 60,
                    "unmarked": 30,
                    "no": 0,
                },
            },
            "kerb": {
                "type": "categorical",
                "field": "associated_kerbs",
                "applies_to": ["crossing"],
                "aggregation": "minimum",
                "factor_weight": 5.0,
                "unknown_grade": 30,
                "values": {
                    "flush": 100,
                    "lowered": 95,
                    "no": 75,
                    "rolled": 35,
                    "yes": 20,
                    "raised": 0,
                },
            },
            "tactile_paving": {
                "type": "categorical",
                "field": "associated_tactile_paving",
                "applies_to": ["crossing"],
                "aggregation": "minimum",
                "factor_weight": 1.0,
                "unknown_grade": 50,
                "values": {
                    "yes": 100,
                    "contrasted": 100,
                    "no": 45,
                },
            },
        },
        "barriers": [
            {
                "field": "highway",
                "operator": "equals",
                "value": "steps",
                "reason": "steps",
            },
            {
                "field": "smoothness",
                "operator": "equals",
                "value": "impassable",
                "reason": "impassable_surface",
            },
            {
                "field": "wheelchair",
                "operator": "equals",
                "value": "no",
                "reason": "wheelchair_no",
            },
            {
                "field": "access",
                "operator": "in",
                "value": ["no", "private"],
                "reason": "access_restricted",
            },
            {
                "field": "foot",
                "operator": "in",
                "value": ["no", "private"],
                "reason": "foot_access_restricted",
            },
        ],
        "grade_caps": [
            {
                "field": "associated_kerbs",
                "operator": "contains",
                "value": "raised",
                "applies_to": ["crossing"],
                "max_grade": 15,
                "reason": "raised_kerb",
            },
        ],
        "cost": {
            "grade_multipliers": [
                {"min_grade": 90, "multiplier": 1.00},
                {"min_grade": 75, "multiplier": 1.20},
                {"min_grade": 60, "multiplier": 1.60},
                {"min_grade": 40, "multiplier": 2.50},
                {"min_grade": 20, "multiplier": 5.00},
                {"min_grade": 1, "multiplier": 10.00},
            ],
            "event_penalties_m": {
                "sidewalk": 0,
                "footway": 0,
                "crossing": 15,
                "stairs": None,
            },
        },
    },
    "blind": {
        "label": "Blind or low vision",
        "description": (
            "Prioritizes detectable transitions, tactile information, "
            "controlled crossings and predictable walking surfaces."
        ),
        "routing_mode": "accessibility_grade",
        "provisional": True,
        "speed_kmh": 4.0,
        "factors": {
            "surface": {
                "type": "categorical",
                "field": "surface",
                "factor_weight": 2.0,
                "unknown_grade": 45,
                "values": {
                    "asphalt": 95,
                    "concrete": 100,
                    "paving_stones": 80,
                    "concrete:plates": 75,
                    "ceramic:tiles": 65,
                    "compacted": 65,
                    "sett": 55,
                    "cobblestone": 50,
                    "unhewn_cobblestone": 35,
                    "fine_gravel": 45,
                    "gravel": 35,
                    "wood": 55,
                    "ground": 40,
                    "earth": 35,
                    "dirt": 35,
                    "grass": 30,
                    "sand": 20,
                    "unpaved": 35,
                    "paved": 70,
                },
            },
            "smoothness": {
                "type": "categorical",
                "field": "smoothness",
                "factor_weight": 3.0,
                "unknown_grade": 45,
                "values": {
                    "excellent": 100,
                    "good": 92,
                    "intermediate": 75,
                    "bad": 55,
                    "very_bad": 40,
                    "horrible": 25,
                    "very_horrible": 10,
                    "impassable": 0,
                },
            },
            "width": {
                "type": "numeric_bands",
                "field": "width_m",
                "factor_weight": 1.5,
                "unknown_grade": 50,
                "bands": [
                    {"max": 0.60, "grade": 20},
                    {"max": 0.90, "grade": 45},
                    {"max": 1.20, "grade": 75},
                    {"max": None, "grade": 100},
                ],
            },
            "incline": {
                "type": "directional_numeric_bands",
                "field": "incline_percent",
                "factor_weight": 1.0,
                "unknown_grade": 50,
                "ascending": [
                    {"max": 5.0, "grade": 100},
                    {"max": 8.33, "grade": 80},
                    {"max": 12.5, "grade": 55},
                    {"max": None, "grade": 25},
                ],
                "descending": [
                    {"max": 5.0, "grade": 100},
                    {"max": 8.33, "grade": 75},
                    {"max": 12.5, "grade": 45},
                    {"max": None, "grade": 20},
                ],
            },
            "tactile_paving": {
                "type": "categorical",
                "field": "associated_tactile_paving",
                "applies_to": ["crossing"],
                "aggregation": "minimum",
                "factor_weight": 6.0,
                "unknown_grade": 15,
                "values": {
                    "yes": 100,
                    "contrasted": 100,
                    "no": 0,
                },
            },
            "kerb_detectability": {
                "type": "categorical",
                "field": "associated_kerbs",
                "applies_to": ["crossing"],
                "aggregation": "minimum",
                "factor_weight": 4.0,
                "unknown_grade": 30,
                "values": {
                    "raised": 65,
                    "yes": 65,
                    "rolled": 55,
                    "lowered": 50,
                    "flush": 25,
                    "no": 20,
                },
            },
            "crossing": {
                "type": "categorical",
                "field": "crossing",
                "applies_to": ["crossing"],
                "factor_weight": 6.0,
                "unknown_grade": 30,
                "values": {
                    "traffic_signals": 90,
                    "zebra": 78,
                    "marked": 72,
                    "uncontrolled": 45,
                    "unmarked": 20,
                    "no": 0,
                },
            },
            "lighting": {
                "type": "categorical",
                "field": "lit",
                "factor_weight": 2.0,
                "unknown_grade": 50,
                "values": {
                    "yes": 100,
                    "automatic": 100,
                    "24/7": 100,
                    "no": 35,
                    "disused": 25,
                },
            },
        },
        "barriers": [
            {
                "field": "smoothness",
                "operator": "equals",
                "value": "impassable",
                "reason": "impassable_surface",
            },
            {
                "field": "access",
                "operator": "in",
                "value": ["no", "private"],
                "reason": "access_restricted",
            },
            {
                "field": "foot",
                "operator": "in",
                "value": ["no", "private"],
                "reason": "foot_access_restricted",
            },
        ],
        "grade_caps": [
            {
                "field": "highway",
                "operator": "equals",
                "value": "steps",
                "max_grade": 40,
                "reason": "steps",
            },
            {
                "field": "associated_kerbs",
                "operator": "contains",
                "value": "raised",
                "applies_to": ["crossing"],
                "max_grade": 35,
                "reason": "raised_crossing_kerb",
            },
        ],
        "cost": {
            "grade_multipliers": [
                {"min_grade": 90, "multiplier": 1.00},
                {"min_grade": 75, "multiplier": 1.15},
                {"min_grade": 60, "multiplier": 1.45},
                {"min_grade": 40, "multiplier": 2.20},
                {"min_grade": 20, "multiplier": 4.50},
                {"min_grade": 1, "multiplier": 8.00},
            ],
            "event_penalties_m": {
                "sidewalk": 0,
                "footway": 0,
                "crossing": 25,
                "stairs": 10,
            },
        },
    },
    "elderly": {
        "label": "Elderly pedestrian",
        "description": (
            "Prioritizes stable, smooth routes with gentle slopes, adequate "
            "width and safer road crossings."
        ),
        "routing_mode": "accessibility_grade",
        "provisional": True,
        "speed_kmh": 3.2,
        "factors": {
            "surface": {
                "type": "categorical",
                "field": "surface",
                "factor_weight": 4.0,
                "unknown_grade": 40,
                "values": {
                    "asphalt": 100,
                    "concrete": 100,
                    "metal": 65,
                    "paving_stones": 82,
                    "paver": 82,
                    "concrete:plates": 72,
                    "ceramic:tiles": 65,
                    "compacted": 65,
                    "fine_gravel": 45,
                    "sett": 40,
                    "cobblestone": 35,
                    "unhewn_cobblestone": 20,
                    "gravel": 30,
                    "wood": 45,
                    "ground": 30,
                    "earth": 25,
                    "dirt": 25,
                    "grass": 20,
                    "sand": 10,
                    "unpaved": 25,
                    "paved": 65,
                },
            },
            "smoothness": {
                "type": "categorical",
                "field": "smoothness",
                "factor_weight": 5.0,
                "unknown_grade": 40,
                "values": {
                    "excellent": 100,
                    "good": 92,
                    "intermediate": 70,
                    "bad": 42,
                    "very_bad": 25,
                    "horrible": 12,
                    "very_horrible": 5,
                    "impassable": 0,
                },
            },
            "width": {
                "type": "numeric_bands",
                "field": "width_m",
                "factor_weight": 3.0,
                "unknown_grade": 40,
                "bands": [
                    {"max": 0.60, "grade": 5},
                    {"max": 0.90, "grade": 30},
                    {"max": 1.20, "grade": 65},
                    {"max": 1.50, "grade": 85},
                    {"max": None, "grade": 100},
                ],
            },
            "incline": {
                "type": "directional_numeric_bands",
                "field": "incline_percent",
                "factor_weight": 5.0,
                "unknown_grade": 40,
                "ascending": [
                    {"max": 2.0, "grade": 100},
                    {"max": 5.0, "grade": 78},
                    {"max": 8.33, "grade": 45},
                    {"max": 12.5, "grade": 15},
                    {"max": None, "grade": 0},
                ],
                "descending": [
                    {"max": 2.0, "grade": 100},
                    {"max": 5.0, "grade": 82},
                    {"max": 8.33, "grade": 52},
                    {"max": 12.5, "grade": 20},
                    {"max": None, "grade": 0},
                ],
            },
            "cross_slope": {
                "type": "numeric_bands",
                "field": "cross_slope_percent",
                "absolute": True,
                "factor_weight": 3.0,
                "unknown_grade": 45,
                "bands": [
                    {"max": 2.0, "grade": 100},
                    {"max": 3.0, "grade": 75},
                    {"max": 5.0, "grade": 40},
                    {"max": None, "grade": 10},
                ],
            },
            "crossing": {
                "type": "categorical",
                "field": "crossing",
                "applies_to": ["crossing"],
                "factor_weight": 5.0,
                "unknown_grade": 35,
                "values": {
                    "traffic_signals": 95,
                    "zebra": 82,
                    "marked": 78,
                    "uncontrolled": 48,
                    "unmarked": 22,
                    "no": 0,
                },
            },
            "kerb": {
                "type": "categorical",
                "field": "associated_kerbs",
                "applies_to": ["crossing"],
                "aggregation": "minimum",
                "factor_weight": 4.0,
                "unknown_grade": 35,
                "values": {
                    "flush": 100,
                    "lowered": 92,
                    "no": 75,
                    "rolled": 42,
                    "yes": 25,
                    "raised": 5,
                },
            },
            "lighting": {
                "type": "categorical",
                "field": "lit",
                "factor_weight": 1.5,
                "unknown_grade": 50,
                "values": {
                    "yes": 100,
                    "automatic": 100,
                    "24/7": 100,
                    "no": 40,
                    "disused": 25,
                },
            },
        },
        "barriers": [
            {
                "field": "smoothness",
                "operator": "equals",
                "value": "impassable",
                "reason": "impassable_surface",
            },
            {
                "field": "access",
                "operator": "in",
                "value": ["no", "private"],
                "reason": "access_restricted",
            },
            {
                "field": "foot",
                "operator": "in",
                "value": ["no", "private"],
                "reason": "foot_access_restricted",
            },
        ],
        "grade_caps": [
            {
                "field": "highway",
                "operator": "equals",
                "value": "steps",
                "max_grade": 12,
                "reason": "steps",
            },
            {
                "field": "associated_kerbs",
                "operator": "contains",
                "value": "raised",
                "applies_to": ["crossing"],
                "max_grade": 15,
                "reason": "raised_kerb",
            },
        ],
        "cost": {
            "grade_multipliers": [
                {"min_grade": 90, "multiplier": 1.00},
                {"min_grade": 75, "multiplier": 1.20},
                {"min_grade": 60, "multiplier": 1.65},
                {"min_grade": 40, "multiplier": 2.60},
                {"min_grade": 20, "multiplier": 5.50},
                {"min_grade": 1, "multiplier": 11.00},
            ],
            "event_penalties_m": {
                "sidewalk": 0,
                "footway": 0,
                "crossing": 22,
                "stairs": 45,
            },
        },
    },
}


SOURCE_CONFIDENCE = {
    "direct_osm_numeric": 100,
    "local_lidar_dtm": 90,
    "regional_dtm": 75,
    "copernicus_glo30": 45,
    "copernicus_glo90": 30,
    "osm_qualitative": 35,
    "missing": 0,
}


DEFAULT_ELEVATION_CONFIG = {
    "enabled": True,
    "providers": [
        {
            "type": "copernicus_glo30",
            "role": "global_primary",
            "priority": 20,
            "cache_dir": ".cache/oswm/elevation/copernicus_glo30",
            "minimum_baseline_m": 45,
            "sample_count": 7,
            "max_abs_slope_percent": 40,
        },
        {
            "type": "copernicus_glo90",
            "role": "global_coverage_fallback",
            "priority": 10,
            "cache_dir": ".cache/oswm/elevation/copernicus_glo90",
            "minimum_baseline_m": 135,
            "sample_count": 7,
            "max_abs_slope_percent": 40,
        },
    ],
    "request_timeout_seconds": 120,
}

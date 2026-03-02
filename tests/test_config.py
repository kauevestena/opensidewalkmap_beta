import re
import numbers
from collections.abc import Sequence

import config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_PARAMS = {
    "CITY_NAME": str,
    "CITY_SHORTNAME": str,
    "USERNAME": str,
    "REPO_NAME": str,
    "BOUNDING_BOX": Sequence,
    "MID_LAT": numbers.Real,
    "MID_LGT": numbers.Real,
    "INITIAL_Z_LEVEL": int,
    "TILES_MIN_ZOOM": int,
    "TILES_MAX_ZOOM": int,
    "OTHER_FOOTWAY_RULES": dict,
    "OTHER_FOOTWAY_EXCLUSION_RULES": dict,
    "other_footways_subcatecories": dict,
}

# ---------------------------------------------------------------------------
# Tests – presence and types
# ---------------------------------------------------------------------------

def test_required_parameters_exist():
    """Every expected config parameter must be defined and non-None."""
    for attr in EXPECTED_PARAMS:
        assert hasattr(config, attr), f"{attr} is missing from config"
        assert getattr(config, attr) is not None, f"{attr} must not be None"


def test_parameter_types():
    """Each parameter must match its expected type."""
    for attr, expected_type in EXPECTED_PARAMS.items():
        value = getattr(config, attr)
        assert isinstance(value, expected_type), (
            f"{attr} should be {expected_type.__name__}, got {type(value).__name__}"
        )


# ---------------------------------------------------------------------------
# Tests – string parameters
# ---------------------------------------------------------------------------

def test_string_parameters_non_empty():
    """String parameters must not be blank."""
    for attr in ("CITY_NAME", "CITY_SHORTNAME", "USERNAME", "REPO_NAME"):
        value = getattr(config, attr)
        assert isinstance(value, str) and value.strip(), f"{attr} must not be empty"


def test_city_shortname_format():
    """CITY_SHORTNAME must be lowercase with no special characters (only a-z, 0-9, _)."""
    shortname = config.CITY_SHORTNAME
    assert re.fullmatch(r"[a-z0-9_]+", shortname), (
        f"CITY_SHORTNAME '{shortname}' must be lowercase alphanumeric with underscores only"
    )


# ---------------------------------------------------------------------------
# Tests – bounding box
# ---------------------------------------------------------------------------

def test_bounding_box_structure():
    """BOUNDING_BOX must be a sequence of exactly four numeric values."""
    bbox = config.BOUNDING_BOX
    assert isinstance(bbox, Sequence), "BOUNDING_BOX must be a sequence"
    assert len(bbox) == 4, "BOUNDING_BOX must have exactly four elements"
    for i, value in enumerate(bbox):
        assert isinstance(value, numbers.Real), f"BOUNDING_BOX[{i}] must be numeric"


def test_bounding_box_ranges():
    """Latitudes must be in [-90, 90] and longitudes in [-180, 180]."""
    south, west, north, east = config.BOUNDING_BOX
    for label, lat in [("south", south), ("north", north)]:
        assert -90 <= lat <= 90, f"{label} latitude {lat} is out of [-90, 90]"
    for label, lon in [("west", west), ("east", east)]:
        assert -180 <= lon <= 180, f"{label} longitude {lon} is out of [-180, 180]"


def test_bounding_box_ordering():
    """Southern latitude < northern; western longitude < eastern."""
    south, west, north, east = config.BOUNDING_BOX
    assert south < north, "southern latitude must be less than northern latitude"
    assert west < east, "western longitude must be less than eastern longitude"


# ---------------------------------------------------------------------------
# Tests – midpoint coordinates
# ---------------------------------------------------------------------------

def test_midpoint_ranges():
    """MID_LAT must be in [-90, 90] and MID_LGT in [-180, 180]."""
    assert -90 <= config.MID_LAT <= 90, f"MID_LAT {config.MID_LAT} is out of range"
    assert -180 <= config.MID_LGT <= 180, f"MID_LGT {config.MID_LGT} is out of range"


def test_midpoint_within_bounding_box():
    """The map midpoint should fall within the bounding box."""
    south, west, north, east = config.BOUNDING_BOX
    assert south <= config.MID_LAT <= north, (
        f"MID_LAT {config.MID_LAT} is outside bounding box latitudes [{south}, {north}]"
    )
    assert west <= config.MID_LGT <= east, (
        f"MID_LGT {config.MID_LGT} is outside bounding box longitudes [{west}, {east}]"
    )


# ---------------------------------------------------------------------------
# Tests – zoom levels
# ---------------------------------------------------------------------------

def test_zoom_levels_positive():
    """All zoom levels must be positive integers."""
    for attr in ("INITIAL_Z_LEVEL", "TILES_MIN_ZOOM", "TILES_MAX_ZOOM"):
        value = getattr(config, attr)
        assert isinstance(value, int), f"{attr} must be an integer"
        assert value > 0, f"{attr} must be positive"


def test_zoom_level_ranges():
    """Zoom levels should be within typical web-map bounds (1–22)."""
    for attr in ("INITIAL_Z_LEVEL", "TILES_MIN_ZOOM", "TILES_MAX_ZOOM"):
        value = getattr(config, attr)
        assert 1 <= value <= 22, f"{attr}={value} is outside the typical range [1, 22]"


def test_tile_zoom_ordering():
    """TILES_MIN_ZOOM must be less than TILES_MAX_ZOOM."""
    assert config.TILES_MIN_ZOOM < config.TILES_MAX_ZOOM, (
        "TILES_MIN_ZOOM must be less than TILES_MAX_ZOOM"
    )


# ---------------------------------------------------------------------------
# Tests – footway rule dictionaries
# ---------------------------------------------------------------------------

def _assert_dict_of_string_lists(value, name):
    """Check that *value* is a dict mapping strings to lists of strings."""
    assert isinstance(value, dict), f"{name} must be a dict"
    for key, vals in value.items():
        assert isinstance(key, str), f"keys in {name} must be strings"
        assert isinstance(vals, list), f"{name}['{key}'] must be a list"
        for item in vals:
            assert isinstance(item, str), (
                f"all items in {name}['{key}'] must be strings"
            )


def test_other_footway_rules_structure():
    """OTHER_FOOTWAY_RULES must be a dict of string → list[str]."""
    _assert_dict_of_string_lists(config.OTHER_FOOTWAY_RULES, "OTHER_FOOTWAY_RULES")


def test_other_footway_exclusion_rules_structure():
    """OTHER_FOOTWAY_EXCLUSION_RULES must be a dict of string → list[str]."""
    _assert_dict_of_string_lists(
        config.OTHER_FOOTWAY_EXCLUSION_RULES, "OTHER_FOOTWAY_EXCLUSION_RULES"
    )


def test_other_footways_subcategories_structure():
    """other_footways_subcatecories must be a dict of string → dict[str, list[str]]."""
    subcats = config.other_footways_subcatecories
    assert isinstance(subcats, dict), "other_footways_subcatecories must be a dict"
    for cat, rules in subcats.items():
        assert isinstance(cat, str), "subcategory keys must be strings"
        assert isinstance(rules, dict), (
            f"other_footways_subcatecories['{cat}'] must be a dict"
        )
        for key, vals in rules.items():
            assert isinstance(key, str), (
                f"keys in other_footways_subcatecories['{cat}'] must be strings"
            )
            assert isinstance(vals, list), (
                f"other_footways_subcatecories['{cat}']['{key}'] must be a list"
            )
            for item in vals:
                assert isinstance(item, str), (
                    f"items in other_footways_subcatecories['{cat}']['{key}'] must be strings"
                )


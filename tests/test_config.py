import inspect
import numbers
from collections.abc import Sequence

import config


def test_bounding_box_sequence_and_values():
    bbox = config.BOUNDING_BOX
    assert isinstance(bbox, Sequence), "BOUNDING_BOX should be a sequence"
    assert len(bbox) == 4, "BOUNDING_BOX should have four elements"
    for value in bbox:
        assert isinstance(value, numbers.Real), "bounding box values must be numeric"
    south, west, north, east = bbox
    assert south < north, "southern latitude must be less than northern latitude"
    assert west < east, "western longitude must be less than eastern longitude"
    for lat in (south, north):
        assert -90 <= lat <= 90, f"latitude {lat} out of range"
    for lon in (west, east):
        assert -180 <= lon <= 180, f"longitude {lon} out of range"


def test_config_parameters_defined_and_types():
    expected_types = {
        "CITY_NAME": str,
        "CITY_SHORTNAME": str,
        "USERNAME": str,
        "REPO_NAME": str,
        "BOUNDING_BOX": Sequence,
        "MID_LAT": numbers.Real,
        "MID_LGT": numbers.Real,
        "INITIAL_Z_LEVEL": numbers.Real,
        "TILES_MIN_ZOOM": numbers.Real,
        "TILES_MAX_ZOOM": numbers.Real,
        "OTHER_FOOTWAY_RULES": dict,
        "OTHER_FOOTWAY_EXCLUSION_RULES": dict,
        "other_footways_subcatecories": dict,
    }

    config_attrs = {k: v for k, v in vars(config).items() if k.isupper() or k == "other_footways_subcatecories"}

    for attr, typ in expected_types.items():
        assert attr in config_attrs, f"{attr} missing in config"
        value = config_attrs[attr]
        assert value is not None, f"{attr} should not be None"
        if typ is Sequence:
            assert isinstance(value, Sequence), f"{attr} should be a sequence"
        else:
            assert isinstance(value, typ), f"{attr} should be of type {typ.__name__}"
        if isinstance(value, str):
            assert value.strip(), f"{attr} should not be empty"

    missing_keys = [k for k in expected_types if k not in config_attrs]
    assert not missing_keys, f"Missing config parameters: {', '.join(missing_keys)}"


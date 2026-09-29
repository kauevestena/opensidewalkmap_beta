"""Accessibility-aware routing support for OpenSidewalkMap.

The package intentionally keeps the human decisions in
``routing.profile_rules`` and the implementation in separate modules.
"""

from .grading import grade_feature
from .profile_rules import PROFILE_RULESET_VERSION, ROUTING_PROFILES
from .profile_validation import validate_profiles

__all__ = [
    "PROFILE_RULESET_VERSION",
    "ROUTING_PROFILES",
    "grade_feature",
    "validate_profiles",
]

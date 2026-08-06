"""
  setup the variables for your city/territory:

  all of them are mandatory (do not remove any)!!

  This file may be outated, the most recent template is available here:

  https://github.com/kauevestena/oswm_codebase/blob/main/other/templates/config.py

  you can reset the template by running (from node rootfolder): 

  sh oswm_codebase/other/templates/copy_config.sh

"""

# Full city name, it may contain special characters, spaces...
# It can be also the name of a neighborhood if is such a big city or you just want a node for it
# Sometimes being more specific can help, so if you for example want the city of Salvador (Brazil)
# you should use "Salvador, Brazil", since just "Salvador" probably will return "El Salvador", the country
CITY_NAME = "Milan, Italy"

# simple name, spaces must be replaced by underscores, no special characters, all in lowercase
CITY_SHORTNAME = "milan"

# Exact municipal boundary and fleet-specific schedules. GitHub cron values
# use UTC; the managed workflow synchronizer renders these literals without
# executing this configuration file.
OSM_RELATION_ID = 44915
NODE_DAILY_CRON = "17 3 * * *"
NODE_WEEKLY_CRON = "43 4 * * 0"
METADATA_TIMEZONE = "Europe/Rome"

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_USER_AGENT = (
    "OpenSidewalkMap/1.0 (https://github.com/kauevestena/oswm_codebase)"
)
NOMINATIM_TIMEOUT_SECONDS = 30
NOMINATIM_ATTEMPTS = 3
NOMINATIM_BACKOFF_SECONDS = 2

OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
)
OVERPASS_ATTEMPTS_PER_ENDPOINT = 2
OVERPASS_BACKOFF_SECONDS = 5

# username, for adresses
USERNAME = "kauevestena"

# repository name, for many weblink references:
REPO_NAME = "opensidewalkmap_milan"

# BOUNDING BOX:
# by now is mostly a fallback method, if the API fails to download the city polygon using CITY_NAME
# A good tool to find them is: bboxfinder.com
# # entire city:
BOUNDING_BOX = (
    45.3867381,  # SOUTHERNMOST LATITUDE
    9.0408867,   # WESTERNMOST LONGITUDE
    45.5358482,  # NORTHERNMOST LATITUDE
    9.2781103,   # EASTERNMOST LONGITUDE
)

# Set a midpoint for the map AND A Z LEVEL FOR THE INITIAL ZOOM:
MID_LAT = 45.4641943
MID_LGT = 9.1896346
INITIAL_Z_LEVEL = 19

# MIN AND MAX ZOOM LEVELS FOR TILE GENERATION:
# (since there's the 100MB file size limit, for big datasets might be better to stay at 19 or even 18)
TILES_MIN_ZOOM = 9
TILES_MAX_ZOOM = 20


###  THE MORE DELICATE ONES: (leave them unchanged by default, unless you know what you are doing!)

# TAGS FOR ADDITIONAL FOOTWAYS
# you can check the reason behind those default ones at: https://kauevestena.github.io/opensidewalkmap/information/other_footways.html

# Values must all be set as a list, even if there's a single value!!

# depending on local rules, the other types of footways can differ, so you migh tune the options
OTHER_FOOTWAY_RULES = {
    "highway": ["footway", "steps", "living_street", "pedestrian", "track", "path"],
    "foot": ["yes", "designated", "permissive", "destination"],
    "footway": ["alley", "path", "yes"],
    "sidewalk": [
        "no"
    ],  # that's mostly for informal footways, complemented by the exclusion rules for footway
    "sidewalk:both": [
        "no"
    ],  # that's mostly for informal footways, complemented by the exclusion rules for footway
}

# since we download all features containing the tags of the previous rule-set, if there's another tag hierarchically above, we should exclude those features:
OTHER_FOOTWAY_EXCLUSION_RULES = {
    "highway": [
        "trunk",
        "motorway",
        "primary",
        "secondary",
        "trunk_link",
        "motorway_link",
        "primary_link",
        "secondary_link",
    ],
    "access": ["no", "private"],
    "foot": ["no", "use_sidepath", "private"],
}

# # The layer definitions for the other footways:
## WARNING: don't change the layer names or the order of the layers.
# You may change only the definitions in terms of the tags you want to use.
# The employed tags shall be a subset of the ones in OTHER_FOOTWAY_RULES
# any inclusion that might be on OTHER_FOOTWAY_EXCLUSION_RULES will be simply ignored

other_footways_subcatecories = {
    "stairways": {"highway": ["steps"]},
    "main_footways": {
        "highway": ["footway", "living_street", "pedestrian"],
        "foot": ["designated"],
        "footway": ["alley", "path", "yes"],
    },
    "potential_footways": {"highway": ["path", "track"]},
    "informal_footways": {"foot": ["yes", "permissive"]},
    "pedestrian_areas": {},  # defined only by geometry type (Polygon,Multipolygon)
}


# GLOBAL ELEVATION SOURCES
#
# Numeric OSM incline=* remains authoritative. Otherwise the routing and
# hazard modules use the public Copernicus DEM Cloud Optimized GeoTIFFs hosted
# by the AWS Open Data Registry. GLO-30 is preferred; GLO-90 guarantees global
# land coverage where a public 30 m tile is unavailable. Both are digital
# surface models, so derived values describe terrain context rather than a
# surveyed sidewalk or cross slope.
ELEVATION_CONFIG = {
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

HAZARD_TERRAIN_CONFIG = {
    "enabled": True,
    "max_dimension": 1600,
    # Suppress building-scale noise in the global surface model so the layer
    # communicates broad terrain context.
    "smoothing_sigma_pixels": 3.0,
}

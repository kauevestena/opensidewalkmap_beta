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
CITY_NAME = "Curitiba"

# simple name, spaces must be replaced by underscores, no special characters, all in lowercase
CITY_SHORTNAME = "curitiba"

# username, for adresses
USERNAME = "kauevestena"

# repository name, for many weblink references:
REPO_NAME = "opensidewalkmap_beta"

# BOUNDING BOX:
# by now is mostly a fallback method, if the API fails to download the city polygon using CITY_NAME
# A good tool to find them is: bboxfinder.com
# # entire city:
BOUNDING_BOX = (
    -25.6450101000000004,  # SOUTHERNMOST LATITUDE
    -49.3891399999999976,  # WESTERNMOST  LONGITUDE
    -25.3467008999999983,  # NORTHERNMOST LATITUDE
    -49.1843181999999999,  # EASTERNMOST  LONGITUDE
)

# Set a midpoint for the map AND A Z LEVEL FOR THE INITIAL ZOOM:
MID_LAT = -25.46075
MID_LGT = -49.26135
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

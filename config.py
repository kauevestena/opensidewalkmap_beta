"""
  setup the variables for your city:

  all of them are mandatory!!
"""

# Full city name, it may contain special characters, spaces...
CITY_NAME = 'Curitiba'

# simple name, spaces must be replaced by underscores, no special characters, all in lowercase
CITY_SHORTNAME = 'curitiba'

# username, for adresses
USERNAME = 'kauevestena'

# repository name, for many weblink references:
REPO_NAME = 'opensidewalkmap_beta'

# City OSM relation id: (search at  https://nominatim.openstreetmap.org/ui/search.html ):
CITY_RELATION_ID = 'R297514' #as string!!

# BOUNDING BOXES
# A good tool to find them is: bboxfinder.com
# # entire city: 
BOUNDING_BOX = (
    -25.6450101000000004, # SOUTHMOST  LATITUDE
    -49.3891399999999976, # WESTMOST   LONGITUDE
    -25.3467008999999983, # NORTHMOST  LATITUDE
    -49.1843181999999999  # EASTMOST   LONGITUDE
    )

# # A sample of a region of special interest, like the city centre, 
# # It must have sidewalks as geometries and be inside the bigger one!!
BOUNDING_BOX_SAMPLE = (
    -25.46340831586,     # SOUTHMOST  LATITUDE
    -49.26485433156466,  # WESTMOST   LONGITUDE
    -25.45836407828201,  # NORTHMOST  LATITUDE
    -49.257818266840495  # EASTMOST   LONGITUDE
    )

STREAMLIT_URL='https://kauevestena-opensidewalkmap-beta-streamlit-routing-app-52bins.streamlitapp.com/'

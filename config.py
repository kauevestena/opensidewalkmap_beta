"""
  setup the variables for your city:

  all of them are mandatory!!
"""

# Full city name, it may contain special characters, spaces...
CITY_NAME = 'Pato Branco'

# simple name, spaces must be replaced by underscores, no special characters, all in lowercase
CITY_SHORTNAME = 'curitiba'

# username, for adresses
USERNAME = 'johna'

# repository name, for many weblink references:
REPO_NAME = 'opensidewalkmap_curitiba'

# City OSM relation id: (search at  https://nominatim.openstreetmap.org/ui/search.html ):
CITY_RELATION_ID = 'R297514' #as string!!

# # entire city:
BOUNDING_BOX = (
    -25.6450101000000004, # SOUTHMOST
    -49.3891399999999976, # WESTMOST
    -25.3467008999999983, # NORTHMOST
    -49.1843181999999999  # EASTMOST
    )

# # a sample of a region of special interest, like the city centre, 
BOUNDING_BOX_SAMPLE = (
    -25.46340831586,     # SOUTHMOST
    -49.26485433156466,  # WESTMOST
    -25.45836407828201,  # NORTHMOST
    -49.257818266840495  # EASTMOST
    )


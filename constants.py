# intended for common values

# hmtml file name
page_name = "index.html"

# data names
sidewalks_path = 'data/sidewalks.geojson'
crossings_path = 'data/crossings.geojson' 
kerbs_path = 'data/kerbs.geojson'

# # the ten block sample
bounding_box_sample = (-25.46340831586,-49.26485433156466,-25.45836407828201,-49.257818266840495)

# # entire city
bounding_box = (-25.6450101000000004,-49.3891399999999976,-25.3467008999999983,-49.1843181999999999)

# required_fields:
req_fields = {
    'sidewalks':['surface','smoothness','width','incline','tactile_paving','incline:across'],
    'kerbs':['kerb','tactile_paving'],
    'crossings':['crossing','surface','smoothness','traffic_calming'],
}

# max radius to cut off unconnected crossings and kerbs
max_radius_cutoff = 50
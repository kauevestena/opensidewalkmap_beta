# import subprocess, time

# subprocess.run('wget -O https://raw.githubusercontent.com/kauevestena/osm_sidewalkreator/main/osm_fetch.py',shell=True)
# DEPRECATED, now it will have its own version.



# # ############

from osm_fetch import *


# # the ten block sample
# bounding_box = (-25.46340831586,-49.26485433156466,-25.45836407828201,-49.257818266840495)

# # entire city
bounding_box = (-25.6450101000000004,-49.3891399999999976,-25.3467008999999983,-49.1843181999999999)

queries_dict = {
    'kerbs' : {'query':osm_query_string_by_bbox(*bounding_box,interest_key='kerb',node=True,way=False),'geomtype':'Point'},
    'sidewalks': {'query':osm_query_string_by_bbox(*bounding_box,interest_key='footway',interest_value='sidewalk'),'geomtype':'LineString'},
    'crossings': {'query':osm_query_string_by_bbox(*bounding_box,interest_key='footway',interest_value='crossing'),'geomtype':'LineString'}
    }

for key in queries_dict:
    outpath = f'data/{key}.geojson'

    get_osm_data(queries_dict[key]['query'],f'{key}_temp',geomtype=queries_dict[key]['geomtype'],print_response=True,geojson_outpath=outpath)










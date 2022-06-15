# import subprocess, time

# subprocess.run('wget -O https://raw.githubusercontent.com/kauevestena/osm_sidewalkreator/main/osm_fetch.py',shell=True)
# DEPRECATED, now it will have its own version.



# # ############

from osm_fetch import *
from constants import *




queries_dict = {
    'kerbs' : {'query':osm_query_string_by_bbox(*bounding_box,interest_key='kerb',node=True,way=False),'geomtype':'Point'},
    'sidewalks': {'query':osm_query_string_by_bbox(*bounding_box,interest_key='footway',interest_value='sidewalk'),'geomtype':'LineString'},
    'crossings': {'query':osm_query_string_by_bbox(*bounding_box,interest_key='footway',interest_value='crossing'),'geomtype':'LineString'}
    }

for key in queries_dict:
    outpath = f'data/{key}.geojson'

    get_osm_data(queries_dict[key]['query'],f'{key}_temp',geomtype=queries_dict[key]['geomtype'],print_response=True,geojson_outpath=outpath)










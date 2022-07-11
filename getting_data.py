# import subprocess, time

# subprocess.run('wget -O https://raw.githubusercontent.com/kauevestena/osm_sidewalkreator/main/osm_fetch.py',shell=True)
# DEPRECATED, now it will have its own version.



# # ############

from osm_fetch import *
from constants import *
from functions import *
from time import sleep





queries_dict = {
    'kerbs' : {'query':osm_query_string_by_bbox(*bounding_box,interest_key='kerb',node=True,way=False),'geomtype':'Point'},
    'sidewalks': {'query':osm_query_string_by_bbox(*bounding_box,interest_key='footway',interest_value='sidewalk'),'geomtype':'LineString'},
    'crossings': {'query':osm_query_string_by_bbox(*bounding_box,interest_key='footway',interest_value='crossing'),'geomtype':'LineString'}
    }

for key in queries_dict:
    outpath = f'data/{key}_raw.geojson'

    get_osm_data(queries_dict[key]['query'],f'{key}_temp',geomtype=queries_dict[key]['geomtype'],print_response=True,geojson_outpath=outpath)


# to record data aging:
record_datetime('Data Fetching')
sleep(.1)

# generate the "report" of the updating info
gen_updating_infotable_page()






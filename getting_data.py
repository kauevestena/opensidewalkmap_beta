import subprocess, time

subprocess.run('wget -O https://raw.githubusercontent.com/kauevestena/osm_sidewalkreator/main/osm_fetch.py',shell=True)

time.sleep(1)

#adding plugin 

# import sys, os
# import pathlib

# # print(Path('osm_fetch.py').absolute)

# # thx: https://stackoverflow.com/a/33244431/4436950
# path_add = pathlib.Path.home() / 'openSidewalkMap_beta/osm_fetch.py' 

# # print(path_add)

# # thx https://stackoverflow.com/a/595315/4436950 
# # path_add = Path(__file__).parents[3]
# # print(path_add)

# sys.path.append(str(path_add))
# print(sys.path)

# # # dirpath = Path(__file__).parents[0] 
# # # print(dirpath)


# # ############

from osm_fetch import *

bounding_box = (-25.46340831586,-49.26485433156466,-25.45836407828201,-49.257818266840495)

queries_dict = {
    'kerbs' : {'query':osm_query_string_by_bbox(*bounding_box,interest_key='kerb',node=True,way=False),'geomtype':'Point'},
    'sidewalks': {'query':osm_query_string_by_bbox(*bounding_box,interest_key='footway',interest_value='sidewalk'),'geomtype':'LineString'},
    'crossings': {'query':osm_query_string_by_bbox(*bounding_box,interest_key='footway',interest_value='crossing'),'geomtype':'LineString'}
    }

for key in queries_dict:
    outpath = f'{key}.geojson'

    get_osm_data(queries_dict[key]['query'],'',geomtype=queries_dict[key]['geomtype'],geojson_outpath=outpath)








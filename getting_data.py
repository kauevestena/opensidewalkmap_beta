from osm_fetch import *
from constants import *
from functions import *
from time import sleep

import osmnx as ox

if USE_OSMNX:
    queries_dict = {
        'kerbs': {'kerb': True, 'barrier': 'kerb'},
        'sidewalks': {'footway': 'sidewalk'},
        'crossings': {'footway': 'crossing'},
    }
else:
    queries_dict = {
        'kerbs': {'query': osm_query_string_by_bbox(*bounding_box, interest_key='kerb', node=True, way=False), 'geomtype': 'Point'},
        'sidewalks': {'query': osm_query_string_by_bbox(*bounding_box, interest_key='footway', interest_value='sidewalk'), 'geomtype': 'LineString'},
        'crossings': {'query': osm_query_string_by_bbox(*bounding_box, interest_key='footway', interest_value='crossing'), 'geomtype': 'LineString'}
    }


for key in queries_dict:
    outpath = f'data/{key}_raw.geojson'

    if not USE_OSMNX:
        get_osm_data(queries_dict[key]['query'], f'{key}_temp', geomtype=queries_dict[key]
                     ['geomtype'], print_response=True, geojson_outpath=outpath)

    else:
        print('generating ', key, '\n')

        as_gdf = ox.geometries_from_bbox(
            bounding_box[2], bounding_box[0], bounding_box[3], bounding_box[1], queries_dict[key])

        # working around with Fiona couldn't handling columns parsed as lists
        for column in as_gdf.columns:
            if as_gdf[column].dtype == object:
                as_gdf[column] = as_gdf[column].astype(str)

        # small adaptations as OSMNX works differently
        as_gdf.reset_index(inplace=True)
        as_gdf.replace('nan', None, inplace=True)
        as_gdf.rename(columns={'osmid': 'id'}, inplace=True)

        as_gdf.to_file(outpath, driver='GeoJSON')


# to record data aging:
record_datetime('Data Fetching')
sleep(.1)

# generate the "report" of the updating info
gen_updating_infotable_page()

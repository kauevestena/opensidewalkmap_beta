from constants import *
from functions import *
import geopandas as gpd
import pandas as pd

'''

    As separate script as long it's really much more slow compared to the other processes...

    This is script was created to store the versioning info of the OSM Features 

'''


# reading as geodataframes:
sidewalks_gdf = gpd.read_file(sidewalks_path)
crossings_gdf = gpd.read_file(crossings_path)
kerbs_gdf = gpd.read_file(kerbs_path)

gdf_dict = {
    'sidewalks':sidewalks_gdf,
    'crossings':crossings_gdf,
    'kerbs':kerbs_gdf,
    }

for category in gdf_dict:

    data = {
    'osmid' : [],
    'rev_day' : [],
    'rev_month' : [],
    'rev_year' : [],
    'n_revs' : [],
    }

    data['osmid'] = gdf_dict[category]['id']

    print('category: ',category,'\n')

    if category != "kerbs":
        to_include = list(map(get_datetime_last_update,gdf_dict[category]['id']))
    else:
        to_include = list(map(get_datetime_last_update_node,gdf_dict[category]['id']))

    data['n_revs'] = [entry[0] for entry in to_include]
    data['rev_day'] = [entry[1] for entry in to_include]
    data['rev_month'] = [entry[2] for entry in to_include]
    data['rev_year'] = [entry[3] for entry in to_include]

    as_df = pd.DataFrame(data)

    as_df.to_json(f'data/{category}_versioning.json')

# to record data aging:
record_datetime('Versioning Data')
sleep(.1)

# generate the "report" of the updating info
gen_updating_infotable_page()
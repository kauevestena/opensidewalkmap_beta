import geopandas as gpd
import pandas as pd
from constants import * 

# reading as geodataframes:
sidewalks_gdf = gpd.read_file(sidewalks_path)
crossings_gdf = gpd.read_file(crossings_path)
kerbs_gdf = gpd.read_file(kerbs_path)

gdf_dict = {
    'sidewalks':sidewalks_gdf,
    'crossings':crossings_gdf,
    'kerbs':kerbs_gdf,
    }

print(sidewalks_gdf)

# updating info:
sidewalks_updating = pd.read_json(sidewalks_versioning_path)
crossings_updating = pd.read_json(crossings_versioning_path)
kerbs_updating = pd.read_json(kerbs_versioning_path)

updating_dict = {'sidewalks':sidewalks_updating,'crossings':crossings_updating,'kerbs':kerbs_updating}

for key in gdf_dict:
    # gdf_dict[key]['last_update'] = '?'
    updating_dict[key]['last_update'] = updating_dict[key]['rev_day'].astype(str) + "-" + updating_dict[key]['rev_month'].astype(str) + "-" + updating_dict[key]['rev_year'].astype(str)

    gdf_dict[key] = gdf_dict[key].set_index('id').join(updating_dict[key].set_index('osmid')['last_update']).reset_index()

    print(gdf_dict[key]['last_update'].unique())




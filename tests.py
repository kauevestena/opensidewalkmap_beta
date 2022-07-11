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

# keep only relevant fields:
for category in gdf_dict:
    gdf_dict[category] = gdf_dict[category][req_fields[category]]


print(sidewalks_gdf.columns)





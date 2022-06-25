from constants import *
from functions import *
import geopandas as gpd
import pandas as pd



sidewalks_gdf = gpd.read_file(sidewalks_path,index='id')


surface_colors = {}
for surface_type in fields_values_properties['sidewalks']['surface']:
    surface_colors[surface_type] = fields_values_properties['sidewalks']['surface'][surface_type]['color']


sidewalks_gdf['colors'] = sidewalks_gdf['surface']

print(sidewalks_gdf['colors'].replace(surface_colors))
from audioop import cross
from constants import *
import geopandas as gpd

# reading as geodataframes:
sidewalks_gdf = gpd.read_file(sidewalks_path)
crossings_gdf = gpd.read_file(crossings_path)
kerbs_gdf = gpd.read_file(kerbs_path)


# removing unconnected crossings and kerbs:
sidewalks_big_unary_buffer = sidewalks_gdf['geometry'].buffer(max_radius_cutoff)

print(type(sidewalks_big_unary_buffer))

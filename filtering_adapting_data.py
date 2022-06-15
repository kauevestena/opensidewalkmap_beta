from audioop import cross
from operator import index
from constants import *
import geopandas as gpd

# reading as geodataframes:
sidewalks_gdf = gpd.read_file(sidewalks_path,index='id')
crossings_gdf = gpd.read_file(crossings_path,index='id')
kerbs_gdf = gpd.read_file(kerbs_path,index='id')

gdf_dict = {
    'sidewalks':sidewalks_gdf,
    'crossings':crossings_gdf,
    'kerbs':kerbs_gdf,
    }


# # removing unconnected crossings and kerbs:
sidewalks_big_unary_buffer = sidewalks_gdf.to_crs('EPSG:3857').buffer(max_radius_cutoff).to_crs('EPSG:4326').unary_union

# # exporting test:
# # test_gdf = gpd.GeoDataFrame({'id':1,'geometry':sidewalks_big_unary_buffer},crs='EPSG:4326')

# # test_gdf.to_file('test.geojson',driver='GeoJSON')

# removing entries that arent in the buffer:
crossings_gdf = crossings_gdf[~crossings_gdf.disjoint(sidewalks_big_unary_buffer)]

kerbs_gdf = kerbs_gdf[~kerbs_gdf.disjoint(sidewalks_big_unary_buffer)]

# # # exporting test:
# crossings_gdf.to_file('test_crossings.geojson',driver='GeoJSON')
# kerbs_gdf.to_file('test_kerbs.geojson',driver='GeoJSON')

# creating missing columns:
for key in gdf_dict:

    # referencing the geodataframe:
    for req_col in req_fields[key]:
        if not req_col in gdf_dict[key]:
            gdf_dict[key][req_col] = '?'

    gdf_dict[key].fillna('?',inplace=True)

    gdf_dict[key].to_file(f'data/{key}.geojson',driver='GeoJSON')




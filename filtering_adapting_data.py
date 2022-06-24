from constants import *
import pandas as pd
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


# reading the conversion table from  surface and smoothness:
# exported from: https://docs.google.com/spreadsheets/d/18FiIDUV4xGeTskx3R2i841zir_OO1Cdc_zluPLdPq-w/edit#gid=0 

smoothness_surface_conservation = pd.read_csv('data/smoothness_surface_conservationscore.csv',index_col='surface').transpose()


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

# dealing with the data:
for key in gdf_dict:

    # referencing the geodataframe:
    for req_col in req_fields[key]:
        if not req_col in gdf_dict[key]:
            gdf_dict[key][req_col] = '?'

            # also creating a default note 
            gdf_dict[key][f'{req_col}_score'] = default_score

    gdf_dict[key].fillna('?',inplace=True)

    # replacing wrong values with "?" (unknown) or misspelled with the nearest valid:
    for subkey in wrong_misspelled_values[key]:
        gdf_dict[key][subkey].replace(wrong_misspelled_values[key][subkey],inplace=True)
        


    if key == 'sidewalks':
        pass
        # mapping surface+smoothness to score of conservation:

        # mapping surface to notes:

        # creating a simple metric for the 

    if key == 'kerbs':
        pass

    if key == 'crossings':
        pass

    gdf_dict[key].to_file(f'data/{key}.geojson',driver='GeoJSON')




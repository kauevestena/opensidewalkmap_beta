'File'

from constants import *
from functions import *
import pandas as pd
import geopandas as gpd
from time import sleep

import os

print('- Reading Data')

# reading as geodataframes:
sidewalks_gdf = gpd.read_file(sidewalks_path_raw) #,index='id')
crossings_gdf = gpd.read_file(crossings_path_raw) #,index='id')
kerbs_gdf = gpd.read_file(kerbs_path_raw) #,index='id')

# creating fields for scores:
# sidewalks_gdf['final_score'] = 5
# crossings_gdf['final_score'] = 5
# kerbs_gdf['final_score'] = 5

# creating dataframes of scores for joining afterwards:
scores_dfs = {}
scores_dfs_fieldnames = {}
for category in fields_values_properties:
    scores_dfs[category] = {}
    scores_dfs_fieldnames[category] = {}

    # print(scores_dfs)

    for osm_key in fields_values_properties[category]:
        # print(category,' : ',osm_key)
        scores_dfs[category][osm_key],scores_dfs_fieldnames[category][osm_key] = get_score_df(fields_values_properties,category,osm_key)



# putting data in a dict
gdf_dict = {
    'sidewalks':sidewalks_gdf,
    'crossings':crossings_gdf,
    'kerbs':kerbs_gdf,
    }

geom_type_dict = {
    'sidewalks':'LineString',
    'crossings':'LineString',
    'kerbs':'Point',
}

print('- Fetching updating info')
# updating info:
sidewalks_updating = pd.read_json(sidewalks_path_versioning)
crossings_updating = pd.read_json(crossings_path_versioning)
kerbs_updating = pd.read_json(kerbs_path_versioning)

updating_dict = {'sidewalks':sidewalks_updating,'crossings':crossings_updating,'kerbs':kerbs_updating}


# reading the conversion table from  surface and smoothness:
# exported from: https://docs.google.com/spreadsheets/d/18FiIDUV4xGeTskx3R2i841zir_OO1Cdc_zluPLdPq-w/edit#gid=0 
smoothness_surface_conservation = pd.read_csv('data/smoothness_surface_conservationscore.csv',index_col='surface').transpose()


# # removing unconnected crossings and kerbs (preparation):
sidewalks_big_unary_buffer = sidewalks_gdf.to_crs('EPSG:3857').buffer(max_radius_cutoff).to_crs('EPSG:4326').unary_union

# removing entries that arent in the buffer:


# crossings_gdf = crossings_gdf[~crossings_gdf.disjoint(sidewalks_big_unary_buffer)]

# kerbs_gdf = kerbs_gdf[~kerbs_gdf.disjoint(sidewalks_big_unary_buffer)]

# # # exporting test:
# crossings_gdf.to_file('test_crossings.geojson',driver='GeoJSON')
# kerbs_gdf.to_file('test_kerbs.geojson',driver='GeoJSON')

# dealing with the data:
for category in gdf_dict:
    print(category)

    

    if category != 'sidewalks':
        print('- Removing unconnected crossings and kerbs')


        disjointed = gdf_dict[category].disjoint(sidewalks_big_unary_buffer)

        gdf_dict[category][disjointed].to_file(os.path.join('data/disjointed',f'{category}_disjointed.geojson'))

        gdf_dict[category] = gdf_dict[category][~disjointed]


    print(' - Removing features with improper geometry type')
    #removing the ones that aren't of the specific intended geometry type:
    # but first saving them for quality tool:
    outpath_improper = os.path.join('data/improper_geoms',f'{category}_improper_geoms.geojson')
    # the boolean Series:
    are_proper_geom = gdf_dict[category].geometry.type == geom_type_dict[category]
    # saving:
    gdf_dict[category][~are_proper_geom].to_file(outpath_improper)

    # now keeping only the ones with proper geometries:
    gdf_dict[category] = gdf_dict[category][are_proper_geom]

    print('- Filling invalids with "?"')

    # referencing the geodataframe:
    for req_col in req_fields[category]:
        if not req_col in gdf_dict[category]:
            gdf_dict[category][req_col] = '?'

            # also creating a default note 
            gdf_dict[category][f'{req_col}_score'] = default_score


    gdf_dict[category].fillna('?',inplace=True)



    # replacing wrong values with "?" (unknown) or misspelled with the nearest valid:
    for subkey in wrong_misspelled_values[category]:
        gdf_dict[category][subkey].replace(wrong_misspelled_values[category][subkey],inplace=True)
        
    print('- Computing scores')
    # conservation state (as a score):
    if category != 'kerbs':
        gdf_dict[category]['conservation_score'] = [smoothness_surface_conservation[surface][smoothness] for surface,smoothness in zip(gdf_dict[category]['surface'],gdf_dict[category]['smoothness'])]

    # creating a score for each field, based on the "default_scores"
    # in future other categories may be crated
    for osm_key in fields_values_properties[category]:
        # print(category,' : ',osm_key)
        gdf_dict[category] = gdf_dict[category].join(scores_dfs[category][osm_key].set_index(osm_key), on=osm_key)



    if category != 'kerbs':
        # gdf_dict[category]['initial_score'] = 
        # crating aliases
        sf = gdf_dict[category][scores_dfs_fieldnames[category]['surface']]
        co = gdf_dict[category]['conservation_score']

        # harmonic mean:
        gdf_dict[category]['final_score'] = (2*sf*co)/(sf+co)


        # mapping surface+smoothness to score of conservation:

        # mapping surface to notes:

        # creating a simple metric for the 

    if category == 'kerbs':
        # just a mere copy, but it may be improved in the future...

        gdf_dict[category]['final_score'] = gdf_dict[category][scores_dfs_fieldnames[category]['kerb']]

        
        pass

    if category == 'crossings':
        # same as sidewalks but with bonifications

        gdf_dict[category]['final_score'] += gdf_dict[category][scores_dfs_fieldnames[category]['crossing']]


    print('- Adding update data')
    # inserting last update:
    updating_dict[category]['update_date'] = updating_dict[category]['rev_day'].astype(str) + "-" + updating_dict[category]['rev_month'].astype(str) + "-" + updating_dict[category]['rev_year'].astype(str)

    # print(updating_dict[category].set_index('osmid')['last_update'])

    gdf_dict[category] = gdf_dict[category].set_index('id').join(updating_dict[category].set_index('osmid')['update_date']
    # ,rsuffix = 'r_remove',lsuffix = 'l_remove',
    ).reset_index()

    gdf_dict[category]['last_update'] = gdf_dict[category]['update_date']


    gdf_dict[category].to_file(f'data/{category}.geojson',driver='GeoJSON')



# generate the "report" of the updating info
record_datetime('Data Pre-Processing')
sleep(.1)

gen_updating_infotable_page()


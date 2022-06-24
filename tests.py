from constants import *
import geopandas as gpd
import pandas as pd

# smoothness_surface_conservation = pd.read_csv('data/smoothness_surface_conservationscore.csv',index_col='surface').transpose()


sidewalks_gdf = gpd.read_file(sidewalks_path,index='id')


# sidewalks_gdf['smoothness'].replace(['concrete','concrete:plates'],'?',inplace=True)
# sidewalks_gdf['surface'].replace({'betão':'?','paver':'paving_stones'},inplace=True)

print(sidewalks_gdf['surface'].unique())

print(sidewalks_gdf['smoothness'].unique())


# conservation_note = [smoothness_surface_conservation[surface][smoothness] for surface,smoothness in zip(sidewalks_gdf['surface'],sidewalks_gdf['smoothness'])]

# print(conservation_note)

# surface_scores = {'surface':[],'score':[]}
# for key in fields_values_properties['sidewalks']['surface']:
#     surface_scores['surface'].append(key)
#     surface_scores['score'].append(fields_values_properties['sidewalks']['surface'][key]['score_default'])
# surface_scores_df = pd.DataFrame(surface_scores)

def get_score_df(inputdict,category='sidewalks',osm_key='surface',input_field='score_default',output_field_base='score',extra_field='bonus'):

    output_field = f'{category}_{osm_key}_{output_field_base}'
    dict = {osm_key:[],output_field:[]}

    for val_key in inputdict[category][osm_key]:
        dict[osm_key].append(val_key)

        score = inputdict[category][osm_key][val_key][input_field]

        dict[output_field].append(score)

        # check if there were a "bonus" value

    return  pd.DataFrame(dict)


# smoothness_scores_df = get_score_df(fields_values_properties,osm_key='smoothness')


# print(scores_df)

# sidewalks_gdf = sidewalks_gdf.join(surface_scores_df.set_index('surface'), on='surface')

# print(sidewalks_gdf['score'].unique())


scores_dfs = {}
for category in fields_values_properties:
    scores_dfs[category] = {}
    for osm_key in fields_values_properties[category]:

        print('\n',category,' : ',osm_key)
        # print(get_score_df(fields_values_properties,category,osm_key))
        scores_dfs[category][osm_key] = get_score_df(fields_values_properties,category,osm_key)

print(scores_dfs)
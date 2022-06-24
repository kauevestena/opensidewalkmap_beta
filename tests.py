from constants import *
from functions import *
import geopandas as gpd
import pandas as pd

# creating dataframes of scores for joining afterwards:
scores_dfs = {}
scores_dfs_fieldnames = {}
for category in fields_values_properties:
    scores_dfs[category] = {}
    scores_dfs_fieldnames[category] = {}

    print(scores_dfs)

    for osm_key in fields_values_properties[category]:
        print(category,' : ',osm_key)
        print(scores_dfs.keys())
        scores_dfs[category][osm_key],scores_dfs_fieldnames[category][osm_key] = get_score_df(fields_values_properties,category,osm_key)

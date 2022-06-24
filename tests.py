from constants import *
import geopandas as gpd
import pandas as pd

smoothness_surface_conservation = pd.read_csv('data/smoothness_surface_conservationscore.csv',index_col='surface').transpose()


sidewalks_gdf = gpd.read_file(sidewalks_path,index='id')


# sidewalks_gdf['smoothness'].replace(['concrete','concrete:plates'],'?',inplace=True)
# sidewalks_gdf['surface'].replace({'betão':'?','paver':'paving_stones'},inplace=True)

print(sidewalks_gdf['surface'].unique())

print(sidewalks_gdf['smoothness'].unique())


# conservation_note = [smoothness_surface_conservation[surface][smoothness] for surface,smoothness in zip(sidewalks_gdf['surface'],sidewalks_gdf['smoothness'])]

# print(conservation_note)


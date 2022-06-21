# import pandas as pd

# df = pd.read_json('crossings.geojson')

# print(df)

import geopandas as gpd

gdf = gpd.read_file('data/sidewalks.geojson')

gdf.fillna('?',inplace=True)

print(gdf)

# testing again
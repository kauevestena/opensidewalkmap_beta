# import pandas as pd

# df = pd.read_json('crossings.geojson')

# print(df)

import geopandas as gpd

gdf = gpd.read_file('kerbs.geojson')

print(gdf.columns)
# import geopandas as gpd
# import pandas as pd
# import sys
# from os import path
# import bs4
# sys.path.append('.') #worked!!
# from constants import * 
# from functions import *


# sidewalks_gdf = gpd.read_file('./data/sidewalks_raw.geojson')

# sidewalks_as_dict = read_json('./data/sidewalks_raw.geojson')

# print(sidewalks_gdf)



# for i,row in enumerate(sidewalks_gdf.itertuples()):
#     # if getattr(row,'bicycle'):
#     print(getattr(row,'lalala',None))


# a = ['b',1,'c']

# print(map(str,a))

# a = [(1,1),(2,2)]

# print(a)

# print(list(map(list,a)))

from collections import namedtuple


point = namedtuple('point',['x','y'])

point_a = point(1,3)

print(point_a)

print(list(point_a))

print(tuple(point_a))

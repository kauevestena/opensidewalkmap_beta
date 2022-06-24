from constants import *
from functions import *
import geopandas as gpd
import pandas as pd


with open('map.html') as page:
    txt = page.read()

print(txt)
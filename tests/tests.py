import geopandas as gpd
import pandas as pd
import sys
from os import path
import bs4
sys.path.append('.') #worked!!
from constants import * 
from functions import *


# # ############

# print(path.dirname( path.dirname( path.abspath(__file__) ) ))



input_htmlpath = './map.html'

# print(find_html_name('./map.html','folium_map','div','class'))


# # with open(input_htmlpath) as inf:
# #     txt = inf.read()
# #     soup = bs4.BeautifulSoup(txt,features='lxml')

# # refs = soup.find_all('div')

# print(refs)

# print(find_map_ref(input_htmlpath))






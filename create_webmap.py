from ossaudiodev import control_labels
from time import sleep
from turtle import position
import folium
from folium.plugins import FloatImage
from functions import *
from constants import *







# CENTER OF THE MAP:
mid_lat = (bounding_box_sample[0]+bounding_box_sample[2])/2
mid_lgt = (bounding_box_sample[1]+bounding_box_sample[3])/2


# CREATING THE MAP
m = folium.Map(location=[mid_lat, mid_lgt],zoom_start=18,min_zoom=15,max_zoom=25,zoom_control=False,tiles=None,min_lat=bounding_box[0],min_lon=bounding_box[1],max_lat=bounding_box[2],max_lon=bounding_box[3],max_bounds=True)

# TODO: include controlScale



# tile customization

# # positron (in doubt about license):
# folium.TileLayer(tiles='CartoDB positron',max_zoom=25,max_native_zoom=25,opacity=.5).add_to(m)


# standard:
folium.TileLayer(max_zoom=25,max_native_zoom=25,name='OpenStreetMap std.',opacity=.5).add_to(m)

# HUMANITARIAN:
folium.TileLayer(tiles='https://a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png ',max_zoom=25,max_native_zoom=25,name='Humanitarian OSM',opacity=.5,attr='Humanitarian OSM').add_to(m)


# opvnkarte:
folium.TileLayer(tiles=' 	https://tile.memomaps.de/tilegen/{z}/{x}/{y}.png',max_zoom=25,max_native_zoom=25,name='OPVN Karte Transport',opacity=.5,attr='OPVN Karte Transport').add_to(m)



# ADDING LAYERS
folium.GeoJson(sidewalks_path,name='sidewalks',zoom_on_click=True).add_to(m)


# ,popup=folium.GeoJsonPopup(fields=['surface','smoothness']

folium.GeoJson(crossings_path,name='crossings',zoom_on_click=True).add_to(m)


folium.GeoJson(kerbs_path,name='kerbs',marker=folium.CircleMarker(radius=3,kwargs={'color':'#FFFFFF'}),zoom_on_click=True).add_to(m)

# # addinge them as choroplets:
# import geopandas as gpd
# import pandas as pd

# sidewalks_gdf = gpd.read_file(sidewalks_path)

# print(pd.DataFrame(sidewalks_gdf))
# folium.Choropleth(
#     geo_data=sidewalks_path,
#     data=pd.DataFrame(sidewalks_gdf),
#     key_on='feature.id',
#     line_color='blue',
#     line_weight=3,
# )

# AT THE END, CHOROPLET was a no-go

# ,popup=folium.GeoJsonPopup(fields=['kerb','tactile_paving'])

# LAYER CONTROL
folium.LayerControl(collapsed=True).add_to(m)

# LOGO/IMAGES
# thx: https://stackoverflow.com/a/47873895/4436950
logo_path = 'assets/are_sidewalks_acessible_typog.png'

float_image_1 = FloatImage(logo_path,bottom=.5,left=.5).add_to(m)

footer_path = 'assets/footer.png'

float_image_1 = FloatImage(footer_path,bottom=.5,left=0).add_to(m)



## EXTRAS:

# # geocoder
# from folium.plugins import Geocoder
# Geocoder().add_to(m)

# # # locate control
# from folium.plugins import LocateControl
# LocateControl(position='topright').add_to(m)

# # measure control_
# from folium.plugins import MeasureControl
# MeasureControl(position='topright').add_to(m)






# saving the page:
m.save(page_name)
sleep(.2)

# # DEALING DIRECTLY WITH THE HTML FILE:


logo_ref = find_html_name(page_name,logo_path)
style_changer(page_name,logo_ref)


# import bs4

# # thx: https://stackoverflow.com/a/35355433/4436950
# # load  file
# with open(page_name) as inf:
#     txt = inf.read()
#     soup = bs4.BeautifulSoup(txt,features='lxml')


# image_ref = soup.find('img')

# print(image_ref)

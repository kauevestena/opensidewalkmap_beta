from time import sleep
import folium
from folium.plugins import FloatImage
from functions import *

# hmtml file name
page_name = "index.html"


# CENTER OF THE MAP:
bounding_box = (-25.46340831586,-49.26485433156466,-25.45836407828201,-49.257818266840495)

mid_lat = (bounding_box[0]+bounding_box[2])/2
mid_lgt = (bounding_box[1]+bounding_box[3])/2


# CREATING THE MAP
m = folium.Map(location=[mid_lat, mid_lgt],zoom_start=18,max_zoom=25,zoom_control=False,tiles=None)

# tile customization
folium.TileLayer(max_zoom=25,max_native_zoom=25,name='OpenStreetMap',opacity=.5).add_to(m)


# ADDING LAYERS
folium.GeoJson('sidewalks.geojson',name='sidewalks',popup=folium.GeoJsonPopup(fields=['surface','smoothness'])).add_to(m)

folium.GeoJson('crossings.geojson',name='crossings').add_to(m)


folium.GeoJson('kerbs.geojson',name='kerbs',marker=folium.CircleMarker(radius=3,kwargs={'color':'#3388ff'}),popup=folium.GeoJsonPopup(fields=['kerb','tactile_paving'])).add_to(m)

# LAYER CONTROL
folium.LayerControl(collapsed=False).add_to(m)

# LOGO
# thx: https://stackoverflow.com/a/47873895/4436950
logo_path = 'assets/are_sidewalks_acessible_typog.png'

float_image_1 = FloatImage(logo_path,bottom=.5,left=.5).add_to(m)


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

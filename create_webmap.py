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

# # positron (in doubt about license):
# folium.TileLayer(tiles='CartoDB positron',max_zoom=25,max_native_zoom=25,opacity=.5).add_to(m)


# standard:
folium.TileLayer(max_zoom=25,max_native_zoom=25,name='OpenStreetMap std.',opacity=.5).add_to(m)

# HUMANITARIAN:
folium.TileLayer(tiles='https://a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png ',max_zoom=25,max_native_zoom=25,name='Humanitarian OSM',opacity=.5,attr='Humanitarian OSM').add_to(m)


# opvnkarte:
folium.TileLayer(tiles=' 	https://tile.memomaps.de/tilegen/{z}/{x}/{y}.png',max_zoom=25,max_native_zoom=25,name='OPVN Karte Transport',opacity=.5,attr='OPVN Karte Transport').add_to(m)



# ADDING LAYERS
folium.GeoJson('data/sidewalks.geojson',name='sidewalks').add_to(m)


# ,popup=folium.GeoJsonPopup(fields=['surface','smoothness']

folium.GeoJson('data/crossings.geojson',name='crossings').add_to(m)


folium.GeoJson('data/kerbs.geojson',name='kerbs',marker=folium.CircleMarker(radius=3,kwargs={'color':'#FFFFFF'})).add_to(m)

# ,popup=folium.GeoJsonPopup(fields=['kerb','tactile_paving'])

# LAYER CONTROL
folium.LayerControl(collapsed=False,).add_to(m)

# LOGO/IMAGES
# thx: https://stackoverflow.com/a/47873895/4436950
logo_path = 'assets/are_sidewalks_acessible_typog.png'

float_image_1 = FloatImage(logo_path,bottom=.5,left=.5).add_to(m)

footer_path = 'assets/footer.png'

float_image_1 = FloatImage(footer_path,bottom=.5,left=0).add_to(m)



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

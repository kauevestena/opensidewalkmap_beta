from time import sleep
import geopandas as gpd
import folium
from folium.plugins import FloatImage
from functions import *
from constants import *
from webmap_insertions import *


print('reading data...')

# reading also as geodataframes:
sidewalks_gdf = gpd.read_file(sidewalks_path,index='id')
crossings_gdf = gpd.read_file(crossings_path,index='id')
kerbs_gdf = gpd.read_file(kerbs_path,index='id')


# keeping only really required fields
extra_fields = ['id','geometry']

sidewalks_gdf = sidewalks_gdf[req_fields['sidewalks']+extra_fields]
crossings_gdf = crossings_gdf[req_fields['crossings']+extra_fields]
kerbs_gdf = kerbs_gdf[req_fields['kerbs']+extra_fields]


gdf_dict = {
    'sidewalks': sidewalks_gdf,
    'crossings': crossings_gdf,
    'kerbs' : kerbs_gdf,
}

type_dict = {
    'sidewalks': 'way',
    'crossings': 'way',
    'kerbs' : 'node',
}


# formatting "id" field as a formatted "osm_id":
for category in gdf_dict:
    if category == 'kerbs':
        gdf_dict[category]['osm_id'] = gdf_dict[category]['id'].astype('string').apply(return_weblink_node)
    else:
        gdf_dict[category]['osm_id'] = gdf_dict[category]['id'].astype('string').apply(return_weblink_way)


'''

    MAP CREATION

'''

print('Creating Map...')


# CENTER OF THE MAP:
mid_lat = (bounding_box_sample[0]+bounding_box_sample[2])/2
mid_lgt = (bounding_box_sample[1]+bounding_box_sample[3])/2


# CREATING THE MAP
m = folium.Map(location=[mid_lat, mid_lgt],zoom_start=18,min_zoom=min_zoom,
max_zoom=20,
zoom_control=False,tiles=None,min_lat=bounding_box[0],min_lon=bounding_box[1],max_lat=bounding_box[2],max_lon=bounding_box[3],max_bounds=True)

# TODO: include controlScale



# tile customization

# # positron (in doubt about license):
# folium.TileLayer(tiles='CartoDB positron',max_zoom=25,max_native_zoom=25,opacity=.5).add_to(m)

# # # darkmatter (in doubt about license):
# folium.TileLayer(tiles='CartoDB dark_matter',max_zoom=25,max_native_zoom=25,opacity=.5).add_to(m)


'''

    TILESETS (BASEMAP LAYERS)

'''


# standard:
folium.TileLayer(name='OpenStreetMap std.',
min_zoom=min_zoom,
opacity=.5,max_zoom=25,max_native_zoom=19).add_to(m)

# cycloMAP:
folium.TileLayer(tiles='https://{switch:a,b,c}.tile-cyclosm.openstreetmap.fr/cyclosm/{zoom}/{x}/{y}.png',name='CyclOSM',opacity=.5,attr='CyclOSM',
min_zoom=min_zoom,max_zoom=25,max_native_zoom=18).add_to(m)

# HUMANITARIAN:
folium.TileLayer(tiles='https://a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png',name='Humanitarian OSM',opacity=.5,attr='Humanitarian OSM',
min_zoom=min_zoom,max_zoom=25,max_native_zoom=18).add_to(m)


# opvnkarte:
folium.TileLayer(tiles='https://tile.memomaps.de/tilegen/{z}/{x}/{y}.png',max_zoom=25,max_native_zoom=18,name='OPVN Karte Transport',opacity=.5,attr='OPVN Karte Transport',
min_zoom=min_zoom).add_to(m)

'''

### STYLING SIDEWALKS AND CROSSINGS:


'''

# for 'surface' tag 
surface_colors =  get_attr_dict(fields_values_properties) # {}
sidewalks_gdf['surface_color'] = sidewalks_gdf['surface']
sidewalks_gdf['surface_color'].replace(surface_colors,inplace=True)

# for 'smoothness' tag 
smoothness_colors =  get_attr_dict(fields_values_properties,osm_tag='smoothness') # {}
sidewalks_gdf['smoothness_color'] = sidewalks_gdf['smoothness']
sidewalks_gdf['smoothness_color'].replace(smoothness_colors,inplace=True)

def style_sidewalk_surface(feature):
    # real thanks to: https://gis.stackexchange.com/questions/394219/folium-draw-polygons-with-distinct-colours 
    return {'color':feature['properties']['surface_color'], 'weight':5.5}

def style_sidewalk_smoothness(feature):
    # real thanks to: https://gis.stackexchange.com/questions/394219/folium-draw-polygons-with-distinct-colours 
    return {'color':feature['properties']['smoothness_color'], 'weight':5.5}

def outline_style(feature):
    return {'color':'black','weight':6.5,}


def simple_highlight(feature):
    return {'weight':12 }

print('Styling...')


### STYLING crossings:

# for 'crossing' tag 
crossing_colors =  get_attr_dict(fields_values_properties,category='crossings',osm_tag='crossing') # {}

# dasharray:
crossing_dash =  get_attr_dict(fields_values_properties,category='crossings',osm_tag='crossing',attr='dasharray') # {}

# dashoffset:
crossing_dashoffset =  get_attr_dict(fields_values_properties,category='crossings',osm_tag='crossing',attr='dashoffset') # {}

# dealing with uncanny/mistaken values
# TODO: create a "wrong value" report
for value in crossings_gdf['crossing'].unique():
    if not value in crossing_colors.keys():
        crossing_colors[value] = '#000000'
        crossing_dash[value] = '20'
        crossing_dashoffset[value] = '50'



crossings_gdf['crossing_colors'] = crossings_gdf['crossing']
crossings_gdf['crossing_colors'].replace(crossing_colors,inplace=True)

crossings_gdf['crossing_dash'] = crossings_gdf['crossing']
crossings_gdf['crossing_dash'].replace(crossing_dash,inplace=True)


crossings_gdf['crossing_dashoffset'] = crossings_gdf['crossing']
crossings_gdf['crossing_dashoffset'].replace(crossing_dashoffset,inplace=True)

def style_crossing(feature):
    # real thanks to: https://gis.stackexchange.com/questions/394219/folium-draw-polygons-with-distinct-colours 
    return {'color':feature['properties']['crossing_colors'], 'weight':4,'dashArray':feature['properties']['crossing_dash'],'dashOffset':feature['properties']['crossing_dashoffset'],'opacity':.6}

# # ADDING LAYERS
# # # dummy version, as a background


'''

    DUMMY LAYERS

'''

# sidewalks
folium.GeoJson(data=sidewalks_gdf
,name='sidewalks_dummy',
style_function= outline_style,control=False
).add_to(m)

# # crossings
# folium.GeoJson(data=crossings_gdf
# ,name='crossings_dummy',
# style_function= outline_style,control=False
# ).add_to(m)

# # kerbs
# folium.GeoJson(data=kerbs_gdf
# ,name='kerbs_dummy',
# style_function= outline_style,control=False
# ).add_to(m)

'''

    **** SIDEWALKS

'''

folium.GeoJson(data=sidewalks_gdf
# sidewalks_path
,name='Sidewalks (surface)',
popup=folium.GeoJsonPopup(fields=req_fields['sidewalks']),
# zoom_on_click=True,
style_function= style_sidewalk_surface,
highlight_function=simple_highlight,
# tooltip='Sidewalk',

tooltip=folium.Tooltip('<b>Sidewalk</b><br>(click for details)','text-align:center')


).add_to(m)

folium.GeoJson(data=sidewalks_gdf
# sidewalks_path
,name='Sidewalks (smoothness)',
popup=folium.GeoJsonPopup(fields=req_fields['sidewalks']),
# zoom_on_click=True,
style_function= style_sidewalk_smoothness,
highlight_function=simple_highlight,
# tooltip='Sidewalk',

tooltip=folium.Tooltip('<b>Sidewalk</b><br>(click for details)','text-align:center'),


show=False
).add_to(m)

'''

    **** CROSSINGS

'''


folium.GeoJson(data=crossings_gdf,name='crossings',
popup=folium.GeoJsonPopup(fields=req_fields['crossings']),
highlight_function=simple_highlight,
# zoom_on_click=True,
style_function=style_crossing,
# tooltip='Crossing',
tooltip=folium.Tooltip('<b>Crossing</b><br>(click for details)','text-align:center')


).add_to(m)


'''

############# KERBS


'''

kerbs_colors =  get_attr_dict(fields_values_properties,category='kerbs',osm_tag='kerb') # {}

kerbs_gdf['kerbs_colors'] = kerbs_gdf['kerb']
kerbs_gdf['kerbs_colors'].replace(kerbs_colors,inplace=True)

def styling_kerbs(feature):
    return {'color':'black','fillColor':feature['properties']['kerbs_colors'],'fillOpacity':1}

folium.GeoJson(data=kerbs_gdf,
name='kerbs',
marker=folium.Circle(
    radius=1,fill=True,weight=1),
popup=folium.GeoJsonPopup(fields=req_fields['kerbs']),
# zoom_on_click=True,
highlight_function=simple_highlight,
style_function=styling_kerbs,

# tooltip='<b>Kerb</b><br>(click for details)',
tooltip=folium.Tooltip('<b>Kerb</b><br>(click for details)','text-align:center')



).add_to(m)

'''

# # # # # # KERBS TACTILE PAVING
 
 
'''

kerbs_tactilepaving_opacity =  get_attr_dict(fields_values_properties,category='kerbs',osm_tag='tactile_paving',attr='opacity') # {}

# print(kerbs_tactilepaving_colors)

kerbs_gdf['kerbs_tactilepaving_opacity'] = kerbs_gdf['tactile_paving']
kerbs_gdf['kerbs_tactilepaving_opacity'].replace(kerbs_tactilepaving_opacity,inplace=True)

# print(kerbs_tactilepaving_opacity)
# print(kerbs_gdf['kerbs_tactilepaving_opacity'])

def styling_kerbs_tac_paving(feature):
    return {
        'opacity':0,
    'fillColor':'black','fillOpacity':feature['properties']['kerbs_tactilepaving_opacity']}


folium.GeoJson(data=kerbs_gdf,
name='kerbs_tp',
control=False,
marker=folium.Circle(
    radius=.4,fill=True,weight=0.1),
style_function=styling_kerbs_tac_paving,
).add_to(m)


'''

    SIDEWALKS TACTILE PAVING

'''

def tp_sw_style(feature):
    return {'color':'black','weight':.5,'opacity':.7}

sw_tp_gdf = sidewalks_gdf.loc[sidewalks_gdf.set_index(['tactile_paving']).index.isin(['yes','contrasted'])]


# sidewalks tactile paving
folium.GeoJson(data=sw_tp_gdf
,name='sidewalks_tactile_paving_layer',
style_function= tp_sw_style,
control=False
).add_to(m)

print('Creating Resources...')


'''

    LAYER CONTROL

'''


# LAYER CONTROL
folium.LayerControl(collapsed=True).add_to(m)


'''

    IMAGES

'''

# LOGO/IMAGES
# thx: https://stackoverflow.com/a/47873895/4436950
logo_path = 'assets/are_sidewalks_acessible_typog.png'

float_image_1 = FloatImage(logo_path,bottom=.5,left=.5).add_to(m)

footer_path = 'assets/footer.png'

float_image_2 = FloatImage(footer_path,bottom=.5,left=0).add_to(m)



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

print('Modifying HTML...')


'''

    SAVING HTML

'''


# saving the page:
m.save(page_name)
sleep(.2)


'''

# # DEALING DIRECTLY WITH THE HTML FILE:

'''

# LOGO style changing

logo_ref = find_html_name(page_name,logo_path)
style_changer(page_name,logo_ref)


# applying a rule to hide footer message for small screens
footer_ref = find_html_name(page_name,footer_path)

footer_img_css_add = ''' 

@media (max-width:1230px) {
  img#''' + footer_ref+ '''{
    display: none;
  }
} 

'''

style_changer(page_name,logo_ref,new=None,append=footer_img_css_add)

# SETTING MAP AS A FIXED ELEMENT:


style_changer(page_name,find_map_ref(page_name),original='relative',new='fixed')



# adding for every entry on the dict
for insertion_point in insertions_dict:
    print(insertion_point)

    # add_to_page_after_first_tag(page_name,insertions_dict[insertion_point],insertion_point)

    replace_at_html(page_name,insertion_point,insertions_dict[insertion_point])

replace_at_html(page_name,'<html>','<html lang="en">')
# import bs4

# # thx: https://stackoverflow.com/a/35355433/4436950
# # load  file
# with open(page_name) as inf:
#     txt = inf.read()
#     soup = bs4.BeautifulSoup(txt,features='lxml')


# image_ref = soup.find('img')

# print(image_ref)

print('Generating updating info...')


# updating record:
record_datetime('Webmap Generation')

# generate the "report" of the updating info
gen_updating_infotable_page()
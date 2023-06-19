import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import osmnx as ox
# from collections import deque
# from copy import deepcopy
from shapely.geometry import LineString
import requests
from oswm_codebase.constants import *

graph_geojson_path = 'osmnx_routing/sample_routing.geojson'
graph_path = 'osmnx_routing/routing_graph.graphml'
sample_as_gdf = gpd.read_file(graph_geojson_path)


###### link at streamlit:
# https://kauevestena-opensidewalkmap-beta-streamlit-routing-app-52bins.streamlitapp.com 

# CONSTANTS

LEN_CRS = sample_as_gdf.estimate_utm_crs()
MAX_DISTANCE = 50
WIDTH = 1000
MAP_KEY = 'folium_map'




# STREAMLIT PAGE CONFIGURATION

print('begin')



# STREAMLIT SETUP

st.set_page_config('OSWM Routing','assets/homepage/favicon_homepage.png','wide','expanded')



# In-page title:
st.header('OSWM Routing App - [see the presentation](https://docs.google.com/presentation/d/e/2PACX-1vQR6zzLLoLE2p90saW3FRCeiEo1w5NEeHFzfbgeaMiQyHRJGXg3nVTfTYi_gb0nGAlYA-GUqJScL0cr/pub?start=false&loop=true&delayms=5000)')


##### Device Type Selection

device_type = st.radio('select device type:',('desktop','mobile'),horizontal=True)

if device_type == 'mobile':
    print('selected mobile')
    WIDTH = 400
    MAP_KEY = 'folium_map_mobile'

else:
    WIDTH = 1000
    MAP_KEY = 'folium_map'

    

st.write('Welcome!! The first click will set Origin, the Second will set Destination, and the Third may be needed to draw the route')

col1, col2, col3, col4 = st.columns([1,1,1,1])

# initializing session state stuff:

if 'waypoints' not in st.session_state:
    st.session_state.waypoints = [None,None,None,None,]

if 'waypoints2' not in st.session_state:
    st.session_state.waypoints2 = [None,None,None,None,]

if 'routing_gdf' not in st.session_state:
    st.session_state.routing_gdf = gpd.GeoDataFrame()

if 'routing_gdf_shortest' not in st.session_state:
    st.session_state.routing_gdf_shortest = gpd.GeoDataFrame()


### FUNCTIONS

def simple_highlight(feature):
    return {'weight':12 }


def json_to_gpx_string(json_string):
    response = requests.post('http://ogre.adc4gis.com/convertJson/',{'json':json_string,'format':'GPX'})

    return response.text


def route_to_gdf(inputgraph,routenodes):
    route_linestring = LineString(
        [(inputgraph.nodes[node_id]['x'],route_graph.nodes[node_id]['y'],route_graph.nodes[node_id]['elevation']) for node_id in routenodes]
    )

    data = {'type':['route']}

    return gpd.GeoDataFrame(data,geometry=[route_linestring],crs='EPSG:4326')


# getting Session State ID:
def get_session_id(cutsize=60):
    keys_list = list(st.session_state.keys())

    for key in keys_list:
        if type(key) == str:
            if len(key) > cutsize:
                return key
            # i would prefer another solution...
            # TODO: find a better one


    return None


ss_id = get_session_id()



# def

# try:

# if "ROUTE_GDF" in globals():
#     print(globals()["ROUTE_GDF"])

# # except:
# #     pass

# ROUTE_GDF = None

# print(ROUTE_GDF)

# @st.cache
# def permanent_stuff():






# @st.cache # for optimization
# def load_routegraph(inputpath):
#     return ox.load_graphml(inputpath,edge_dtypes={'beta_wh_weight':float})

# route_graph = load_routegraph(graph_path)

route_graph = ox.load_graphml(graph_path,edge_dtypes={'beta_wh_weight':float})


# m = ox.plot_graph_folium(route_graph,
# # popup_attribute='beta_wh_weight',
# tiles='OpenStreetMap',fit_bounds=True)

# # edges_datapath = 'osmnx_routing/sample_routing.geojson'

# edges_data = gpd.read_file(edges_datapath)


# CENTER OF THE MAP:
mid_lat = (BOUNDING_BOX_SAMPLE[0]+BOUNDING_BOX_SAMPLE[2])/2
mid_lgt = (BOUNDING_BOX_SAMPLE[1]+BOUNDING_BOX_SAMPLE[3])/2

# m = folium.Map(location=[-25.460765491025665,-49.2613971233368],
m = folium.Map(location=[mid_lat,mid_lgt],
               
# height=600,
# position='absolute',
zoom_start=17,
control_scale=True,
zoom_control=False,
)

# add a layer control

folium.Choropleth(graph_geojson_path,
# line_color='#e41a1c',
line_weight=1.5,
highlight=simple_highlight,
name="Available Sidewalks",
).add_to(m)






if 'routing_gdf_shortest' in st.session_state:
    gdf_sh = st.session_state['routing_gdf_shortest']
    if not(gdf_sh.empty):
        folium.Choropleth(gdf_sh,line_color='#e41a1c',line_weight=4,
        name='Shortest Route (RED)',
        highlight=simple_highlight).add_to(m)

        # wp = st.session_state.waypoints

        with col4:

            st.download_button('download Shortest geojson',gdf_sh.to_json(),'oswm_sh_route.geojson','application/json')

        with col2: 
            st.download_button('download Shortest GPX',json_to_gpx_string(gdf_sh.to_json()),'oswm_sh_route.gpx','application/xml')






if 'routing_gdf' in st.session_state:
    gdf_opt = st.session_state['routing_gdf']

    if not(gdf_opt.empty):
        folium.Choropleth(gdf_opt,line_color='#377eb8',line_weight=4,
        name='Optimized Route (BLUE)',
        highlight=simple_highlight).add_to(m)

        # print(st.session_state['waypoints2'])

        folium.Marker(
            location=st.session_state['waypoints2'][0],
            tooltip="Origin",
            # color='blue',
            icon=folium.Icon(color="blue", icon="play"),
            draggable=True,
        ).add_to(m)

        folium.Marker(
            location=st.session_state['waypoints2'][1],
            tooltip="Destination",
            # color='blue',
            icon=folium.Icon(color="blue", icon="flag"),
            draggable=True,
        ).add_to(m)

        with col3:
            st.download_button('download Optimized geojson',gdf_opt.to_json(),'oswm_opt_route.geojson','application/json')

        with col1: 
            st.download_button('download Optimized GPX',json_to_gpx_string(gdf_opt.to_json()),'oswm_opt_route.gpx','application/xml')

# if ROUTE_GDF:
#     folium.Choropleth(ROUTE_GDF).add_to(m)




folium.LayerControl(collapsed=False,position='topleft').add_to(m)



# st_data = permanent_stuff()



# st_data = st_folium(m, width = 1200)
st_data = st_folium(m,MAP_KEY,width=WIDTH)






# print('outer loop\n')

state3 = False

# print(len(ss_id),ss_id)
if ss_id:

    if type(st.session_state[ss_id]) == dict:
        if st.session_state[ss_id]['last_clicked']:


            lgt = st.session_state[ss_id]['last_clicked']['lng']
            lat = st.session_state[ss_id]['last_clicked']['lat']

            # state_before = deepcopy(st.session_state.waypoints)

            # # # #  C3


            if all(st.session_state.waypoints):

                print('c3')
                st.session_state.waypoints = [None,None,None,None,]

                # state3_cond = deepcopy(st.session_state.waypoints)

                # print('cond 3',state3_cond)


                state3 = True


            # # # #  C2

            if st.session_state.waypoints[0] and not st.session_state.waypoints[2]:
                print('c2')
                

                st.session_state.waypoints = [st.session_state.waypoints[0],st.session_state.waypoints[1],lgt,lat]

                # state2_cond = deepcopy(st.session_state.waypoints)


                # print('cond 2',st.session_state.waypoints)

                pO = st.session_state.waypoints[:2]
                pD = st.session_state.waypoints[2:]



                O_nearest,orig_dist = ox.distance.nearest_nodes(route_graph, *pO,return_dist=True)
                D_nearest,dest_dist = ox.distance.nearest_nodes(route_graph, *pD,return_dist=True)

                # if too far from the graph nodes...


                if any((orig_dist<MAX_DISTANCE,dest_dist<MAX_DISTANCE)):


                    optimized_route = ox.distance.shortest_path(route_graph,O_nearest,D_nearest,weight='beta_wh_weight')

                    shortest_route = ox.distance.shortest_path(route_graph,O_nearest,D_nearest)


                    if len(optimized_route) > 1:


                        # optimized_path_polyline  = [(route_graph.nodes[node_id]['x'],route_graph.nodes[node_id]['y']) for node_id in optimized_route]

                        # opt_route_linestring = LineString(optimized_path_polyline)

                        # shortest_path_polyline  = [(route_graph.nodes[node_id]['x'],route_graph.nodes[node_id]['y']) for node_id in shortest_route]

                        # short_route_linestring = LineString(shortest_path_polyline)

                        # data = {'type':['optimized','shortest']}

                        # st.session_state['routing_gdf'] = gpd.GeoDataFrame(data,geometry=[opt_route_linestring,short_route_linestring],crs='EPSG:4326')

                        st.session_state['routing_gdf'] = route_to_gdf(route_graph,optimized_route)

                        st.session_state['routing_gdf_shortest'] = route_to_gdf(route_graph,shortest_route)

                        st.session_state['waypoints2'] = [(pO[1],pO[0]),(pD[1],pD[0])]


                        # print(path_polyline)

                        # folium.PolyLine(path_polyline).add_to(m)

                        # folium.GeoJson(route_gdf).add_to(m)

                        # folium.Choropleth(route_gdf).add_to(m)


                        # st_data2 = st_folium(m, width = 1200)


                        # folium.Choropleth(graph_geojson_path).add_to(m)

                        st.write('Origin:',*pO,'and Destination:',*pD,' All Set!! click again to show the route!')


                else:
                    st.write('One or both points too far from available mapped sidewalks.')









            # # # #  C1
            if not all(st.session_state.waypoints) and not state3:
                print('c1')


                st.session_state.waypoints = [lgt,lat,None,None]

                st.session_state.routing_gdf = gpd.GeoDataFrame()

                st.write('ORIGIN: ',lgt,' , ',lat, ' SET!! (lgt,lat)')

                # state1_cond = deepcopy(st.session_state.waypoints)

                # print('cond 1',state1_cond)


            # state_after = deepcopy(st.session_state.waypoints)

            # print()
            # print(st.session_state)
            # print('before ',state_before)



            # print('after',state_after)



# session state id:

# if st.session_state[ss_id]['last_clicked']:
#     print(st.session_state[ss_id]['last_clicked'])



print('end\n')
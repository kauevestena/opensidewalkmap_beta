from turtle import pos
import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import osmnx as ox
from collections import deque
from copy import deepcopy
from shapely.geometry import LineString
import requests


# STREAMLIT PAGE CONFIGURATION

print('begin')

def simple_highlight(feature):
    return {'weight':12 }

st.set_page_config('OSWM Routing','assets/homepage/favicon_homepage.png','wide','expanded')

# In-page title:
st.header('OSWM Routing App')

st.write('Welcome!! The first click will set Origin, Second the Destination, and the Third may be needed to draw the route')

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


def json_to_gpx_string(json_string):
    response = requests.post('http://ogre.adc4gis.com/convertJson/',{'json':json_string,'format':'GPX'})

    return response.text


def route_to_gdf(inputgraph,routenodes):
    route_linestring = LineString(
        [(inputgraph.nodes[node_id]['x'],route_graph.nodes[node_id]['y']) for node_id in routenodes]
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
MAX_DISTANCE = 50





graph_geojson_path = 'osmnx_routing/sample_routing.geojson'

graph_path = 'osmnx_routing/routing_graph.graphml'

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


m = folium.Map(location=[-25.460765491025665,-49.2613971233368],
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
    if not(st.session_state['routing_gdf_shortest'].empty):
        folium.Choropleth(st.session_state['routing_gdf_shortest'],line_color='#e41a1c',line_weight=4,
        name='Shortest Route (RED)',
        highlight=simple_highlight).add_to(m)

        wp = st.session_state.waypoints




if 'routing_gdf' in st.session_state:
    if not(st.session_state['routing_gdf'].empty):
        folium.Choropleth(st.session_state['routing_gdf'],line_color='#377eb8',line_weight=4,
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

# if ROUTE_GDF:
#     folium.Choropleth(ROUTE_GDF).add_to(m)




folium.LayerControl(collapsed=False,position='topleft').add_to(m)



# st_data = permanent_stuff()



# st_data = st_folium(m, width = 1200)
st_data = st_folium(m,'folim_map',width=1000)






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
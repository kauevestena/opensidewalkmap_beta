import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import osmnx as ox
from collections import deque
from copy import deepcopy
from shapely.geometry import LineString

# STREAMLIT PAGE CONFIGURATION

st.set_page_config('OSWM Routing','assets/homepage/favicon_homepage.png','wide','expanded')

# In-page title:
st.write('OSWM Routing App')

# initializing session state stuff:

if 'waypoints' not in st.session_state:
    st.session_state.waypoints = [None,None,None,None,]

if 'routing_gdf' not in st.session_state:
    st.session_state.routing_gdf = gpd.GeoDataFrame()


# getting Session State ID:
ss_id = list(st.session_state.keys())[0]


print('start')

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

route_graph = ox.load_graphml(graph_path,edge_dtypes={'beta_wh_weight':float})


# m = ox.plot_graph_folium(route_graph,
# # popup_attribute='beta_wh_weight',
# tiles='OpenStreetMap',fit_bounds=True)

# # edges_datapath = 'osmnx_routing/sample_routing.geojson'

# edges_data = gpd.read_file(edges_datapath)


m = folium.Map(location=[-25.460765491025665,-49.2613971233368],
zoom_start=17,
control_scale=True,
zoom_control=False,
)

if not(st.session_state['routing_gdf'].empty):
    print(st.session_state['routing_gdf'])
    folium.Choropleth(st.session_state['routing_gdf'],color='red',wheight=3).add_to(m)


# if ROUTE_GDF:
#     folium.Choropleth(ROUTE_GDF).add_to(m)



# folium.Choropleth(graph_geojson_path).add_to(m)


st_data = st_folium(m, width = 1200)

# st_data = permanent_stuff()








# print('outer loop\n')

state3 = False

if type(st.session_state[ss_id]) == dict:
    if st.session_state[ss_id]['last_clicked']:


        lgt = st.session_state[ss_id]['last_clicked']['lng']
        lat = st.session_state[ss_id]['last_clicked']['lat']

        # state_before = deepcopy(st.session_state.waypoints)


        if all(st.session_state.waypoints):

            print('c3')
            st.session_state.waypoints = [None,None,None,None,]

            # state3_cond = deepcopy(st.session_state.waypoints)

            # print('cond 3',state3_cond)


            state3 = True


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


                shortest = ox.distance.shortest_path(route_graph,O_nearest,D_nearest,weight='beta_wh_weight')

                if len(shortest) > 1:


                    path_polyline  = [(route_graph.nodes[node_id]['x'],route_graph.nodes[node_id]['y']) for node_id in shortest]

                    route_linestring = LineString(path_polyline)

                    dummy_data = {'type':['route']}

                    st.session_state['routing_gdf'] = gpd.GeoDataFrame(dummy_data,geometry=[route_linestring],crs='EPSG:4326')

                    

                    # print(path_polyline)

                    # folium.PolyLine(path_polyline,color='red',weight=3,tooltip='test').add_to(m)

                    # folium.GeoJson(route_gdf).add_to(m)

                    # folium.Choropleth(route_gdf).add_to(m)


                    # st_data2 = st_folium(m, width = 1200)


                    # folium.Choropleth(graph_geojson_path).add_to(m)

                    st.write('Origin:',*pO)
                    st.write('Destination:',*pD)
                    st.write('(Longitude, Latitude)')


            else:
                st.write('One or both points too far from available mapped sidewalks.')










        if not all(st.session_state.waypoints) and not state3:
            print('c1')


            st.session_state.waypoints = [lgt,lat,None,None]

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
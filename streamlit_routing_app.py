import streamlit as st
from streamlit_folium import st_folium
import folium
# import geopandas as gpd
import osmnx as ox
from collections import deque
from copy import deepcopy


st.set_page_config('OSWM Routing','assets/homepage/favicon_homepage.png','wide','auto',)

graph_geojson_path = 'osmnx_routing/sample_routing.geojson'

graph_path = 'osmnx_routing/routing_graph.graphml'

route_graph = ox.load_graphml(graph_path)


# m = ox.plot_graph_folium(route_graph,
# # popup_attribute='beta_wh_weight',
# tiles='OpenStreetMap',fit_bounds=True)

# # edges_datapath = 'osmnx_routing/sample_routing.geojson'

# edges_data = gpd.read_file(edges_datapath)

# folium.GeoJson(edges_datapath).add_to(m)

m = folium.Map(location=[-25.460765491025665,-49.2613971233368],
 zoom_start=17,
 )

folium.Choropleth(graph_geojson_path).add_to(m)


st_data = st_folium(m, width = 1200)

if 'waypoints' not in st.session_state:
    st.session_state.waypoints = [None,None,None,None,]



print('outer loop\n')

state3 = False

if st_data['last_clicked']:


    lgt = st_data['last_clicked']['lng']
    lat = st_data['last_clicked']['lat']

    state_before = deepcopy(st.session_state.waypoints)


    if all(st.session_state.waypoints):


        st.session_state.waypoints = [None,None,None,None,]

        state3_cond = deepcopy(st.session_state.waypoints)

        print('cond 3',state3_cond)


        state3 = True


    if st.session_state.waypoints[0] and not st.session_state.waypoints[2]:

        st.session_state.waypoints = [st.session_state.waypoints[0],st.session_state.waypoints[1],lgt,lat]

        state2_cond = deepcopy(st.session_state.waypoints)

        print('cond 2',state2_cond)




    if not all(st.session_state.waypoints) and not state3:
        st.session_state.waypoints = [lgt,lat,None,None]

        state1_cond = deepcopy(st.session_state.waypoints)

        print('cond 1',state1_cond)


    state_after = deepcopy(st.session_state.waypoints)

    print()
    print(st.session_state)
    print('before ',state_before)



    print('after',state_after)
    



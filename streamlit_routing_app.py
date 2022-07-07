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

# center on Liberty Bell, add marker
m = folium.Map(location=[-25.460765491025665,-49.2613971233368],
 zoom_start=17,
 )

folium.Choropleth(graph_geojson_path).add_to(m)


# folium.Marker(
#     [-25.01, -49.01], 
#     popup="Liberty Bell", 
#     tooltip="Liberty Bell"
# ).add_to(m)

# call to render Folium map in Streamlit
st_data = st_folium(m, width = 1200)

# print()
# print()

# print(st_data)
# print()


# points = deque([])
# points = []

# st.session_state['last_clicks'] = []

# st.session_state['lgt_o'] = None
# st.session_state['lat_o'] = None
# st.session_state['lgt_d'] = None
# st.session_state['lat_d'] = None

# interest_val_keys = ('lgt_o','lat_o','lgt_d','lat_d')

# def print_if_variable_exists(text,var):
#     try:
#         print(text,var)
#     except:
#         pass


if 'waypoints' not in st.session_state:
    st.session_state.waypoints = [None,None,None,None,]


# if 'prev_lat' not in st.session_state:
#     st.session_state.prev_lat = 0

# if 'prev_lgt' not in st.session_state:
#     st.session_state.prev_lat = 0



# if 'lgt_o' not in st.session_state:
#     st.session_state.lgt_o = None

# if 'lat_o' not in st.session_state:
#     st.session_state.lat_o = None

# if 'lgt_d' not in st.session_state:
#     st.session_state.lgt_d = None

# if 'lat_d' not in st.session_state:
#     st.session_state.lat_d = None

# lgt_o = None
# lat_o = None
# lgt_d = None
# lat_d = None

print('outer loop\n')

state3 = False

if st_data['last_clicked']:
    # # # print(st_data['last_clicked'])

    # # # points.append((st_data['last_clicked']['lng'],st_data['last_clicked']['lat']))

    # # # print(points)

    # # # print(list(st.session_state.keys()))

    lgt = st_data['last_clicked']['lng']
    lat = st_data['last_clicked']['lat']

    # # # if not st.session_state['lat_o'] and not st.session_state['lat_d']:
    # # st.session_state['lgt_o'] = lgt
    # # st.session_state['lat_o'] = lat

    # # if st.session_state['lat_o'] and not st.session_state['lat_d']:
    # #     # st.session_state['lgt_o'] = None
    # #     # st.session_state['lat_o'] = None
    # #     st.session_state['lgt_d'] = lgt
    # #     st.session_state['lat_d'] = lat

    # # interest_values = [st.session_state[entry] for entry in interest_val_keys]

    # # if all(interest_values):
    # #     for value in interest_val_keys:
    # #         st.session_state[value] = None

    # # st.write(f'clicked --> lgt: {lgt}, lat: {lat}')

    # # # print(st.session_state)
    # # print(st.session_state)

    # if lgt_o and lgt_d:
    #     lgt_o = None
    #     lat_o = None
    #     lgt_d = None
    #     lat_d = None

    # if lgt_o:
    #     lgt_d = lat
    #     lat_d = lgt

    # lgt_o = lgt
    # lat_o = lat

    # print(lgt_o,lat_o,lgt_d,lat_d)
    # if 

    state_before = deepcopy(st.session_state.waypoints)


    if all(st.session_state.waypoints):
        print('cond 3')

        # st.session_state.waypoints = [st.session_state.waypoints[2],st.session_state.waypoints[3],lgt,lat]

        st.session_state.waypoints = [None,None,None,None,]

        state3_cond = deepcopy(st.session_state.waypoints)

        state3 = True

    # if any(st.session_state.waypoints):
    if st.session_state.waypoints[0] and not st.session_state.waypoints[2]:
        print('cond 2')

        st.session_state.waypoints = [st.session_state.waypoints[0],st.session_state.waypoints[1],lgt,lat]

        state2_cond = deepcopy(st.session_state.waypoints)


        # condition 2

    if not all(st.session_state.waypoints) and not state3:
        print('cond 1')
        st.session_state.waypoints = [lgt,lat,None,None]

        state1_cond = deepcopy(st.session_state.waypoints)







    state_after = deepcopy(st.session_state.waypoints)

    print()
    print(st.session_state)
    print('before ',state_before)

    try:
        print('s 1 '  ,state1_cond)
    except:
        pass

    try:
        print('s 2 '  ,state2_cond)
    except:
        pass

    try:
        print('s 3',state3_cond)
    except:
        pass

    print('after',state_after)
    

    # bubble = deepcopy(st.session_state.prev_lat)

    # # st.session_state.prev_lat -= st.session_state.prev_lat

    # st.session_state.prev_lat += lat

    # st.session_state.prev_lat -= bubble
    

    # print(st.session_state)
    # print(bubble)



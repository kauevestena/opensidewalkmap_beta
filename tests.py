# import osmnx as ox
import geopandas as gpd
import requests
from shapely.geometry import LineString

# graph_path = 'osmnx_routing/routing_graph.graphml'

# route_graph = ox.load_graphml(graph_path,edge_dtypes={'beta_wh_weight':float})


# nodes, edges = ox.graph_to_gdfs(route_graph)

path_polyline  = [(-49,-25),(-48,-26)]

route_linestring = LineString(path_polyline)

dummy_data = {'type':['route']}

sample =  gpd.GeoDataFrame(dummy_data,geometry=[route_linestring],crs='EPSG:4326')

json_string = sample.to_json()

print(json_string)


response = requests.post('http://ogre.adc4gis.com/convertJson/',{'json':json_string,'format':'GPX'})

print(response.text)



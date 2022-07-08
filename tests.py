import osmnx as ox

graph_path = 'osmnx_routing/routing_graph.graphml'

route_graph = ox.load_graphml(graph_path,edge_dtypes={'beta_wh_weight':float})


# nodes, edges = ox.graph_to_gdfs(route_graph)

# print(edges['beta_wh_weight'].unique())



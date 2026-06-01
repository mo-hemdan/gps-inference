#%%
import time
from webbrowser import UnixBrowser
from networkx import edges
import pandas as pd
import numpy as np
import datetime
import os
from geopy.distance import geodesic as GD
import geopandas as gpd
import osmnx as ox
from tqdm import tqdm
from shapely.geometry import Point
import networkx as nx
import uuid
#%%
# Load the trajectory data
input_path = "/project/cs-dmlab/areeg/Metadata/metadata_inference/data/"
file = "top_10_percentage.csv.csv"
df = pd.read_csv(os.path.join(input_path, file))
df.drop([col for col in df.columns if 'Unnamed' in col], axis=1, inplace=True)
timestamp_str = 'timestamp'
lat_str = 'lat'
lon_str = 'lon'
trip_veh_id_str = 'vehicule_id'
df[timestamp_str] = pd.to_datetime(df[timestamp_str])
df = df.sort_values(by=[trip_veh_id_str, timestamp_str])

######### Map match the trajectory to nodes and edges ###########
# Get the graph from the bounding box of the trajectory and project both to the same CRS
lat_col = df[lat_str]
long_col = df[lon_str]
n = max(lat_col)
s = min(lat_col)
e = max(long_col)
w = min(long_col)
network_type = "drive"
bbox = (w, s, e, n)
G = ox.graph_from_bbox(bbox, network_type=network_type, simplify=False, retain_all=True, truncate_by_edge=False)
G_proj = ox.project_graph(G)

gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_str], df[lat_str]), crs='EPSG:4326')
gdf_proj = gdf.to_crs(G_proj.graph['crs'])
long_col_proj = gdf_proj.geometry.x
lat_col_proj = gdf_proj.geometry.y

#%%
# Match the trajectory points to the nearest nodes and edges
edge_list = ox.nearest_edges(G_proj, long_col_proj, lat_col_proj, return_dist=True)
node_list = ox.nearest_nodes(G_proj, long_col_proj, lat_col_proj, return_dist=True)

# Extracting OSM way IDs and edge IDs in a more efficient way
way_ids, edge_ids = zip(*[
    (osmid[0] if isinstance(osmid := G_proj.edges[edge].get('osmid', None), list) else osmid, str(edge))
    for edge in edge_list[0]
])


# Create a GeoDataFrame to store the map-matching results
map_matching_df = gpd.GeoDataFrame({
    lon_str: long_col,
    lat_str: lat_col,
    'node_id': [n for n in node_list[0]],  # Node ID
    # 'node_distance': [n_dist for n_dist in node_list[1]],  # Distance to the node
    # 'nearest_edge': [(u, v) for u, v, _ in edge_list[0]],  # Edge (u, v)
    # 'edge_distance': [e_dist for e_dist in edge_list[1]],  # Distance to the edge
    'way_id': way_ids,  # OSM way ID
    'edge_id': edge_ids  # edge_ids
})


matched_df = df.join(map_matching_df, lsuffix='', rsuffix='_right')
matched_df.drop([c for c in matched_df.columns if '_right' in c], axis=1, inplace=True)

#%%
# map_matching_df
#%%
########## Extract metadata directly from the trajectory ###########
# Calculate the travel time, distance, and speed between consecutive points

matched_df['prev_timestamp'] = matched_df.groupby(trip_veh_id_str)[timestamp_str].shift()
matched_df['prev_lat'] = matched_df.groupby(trip_veh_id_str)[lat_str].shift()
matched_df['prev_lon'] = matched_df.groupby(trip_veh_id_str)[lon_str].shift()

# Compute time difference (avoid NaN errors)
matched_df['travel_time_s'] = (matched_df[timestamp_str] - matched_df['prev_timestamp']).dt.total_seconds()
matched_df['travel_time_s'] = matched_df['travel_time_s'].fillna(0)  # Fill first row NaN with 0

# Compute distance using vectorized haversine calculation
coords1 = list(zip(matched_df['prev_lat'], matched_df['prev_lon']))
coords2 = list(zip(matched_df[lat_str], matched_df[lon_str]))

matched_df['distance_m'] = [GD(p1, p2).m if p1 and p2 and not np.isnan(p1[0]) else 0 for p1, p2 in zip(coords1, coords2)]
matched_df['distance_km'] = [GD(p1, p2).km if p1 and p2 and not np.isnan(p1[0]) else 0 for p1, p2 in zip(coords1, coords2)]

# Compute speed (handle division by zero)
matched_df['speed_mps'] = matched_df['distance_m'] / matched_df['travel_time_s']
matched_df['speed_kmph'] = matched_df['distance_km'] / (matched_df['travel_time_s'] / 3600)

# Handle infinite values and NaN in speed (replace with 0)
matched_df['speed_mps'] = matched_df['speed_mps'].replace([np.inf, -np.inf], 0).fillna(0)
matched_df['speed_kmph'] = matched_df['speed_kmph'].replace([np.inf, -np.inf], 0).fillna(0)

# Drop temporary columns
matched_df.drop(columns=['prev_timestamp', 'prev_lat', 'prev_lon'], inplace=True)


def time_expand(row):
    datetime_obj = row[timestamp_str]
    month = datetime_obj.month
    day = datetime_obj.weekday()
    hour = datetime_obj.hour
    minute = datetime_obj.minute

    if minute > 30:
        hour+=1
        if hour == 24:
            hour = 0

    if day in [0,1,2,3,4]:
        daytype = "weekday"
    elif day in [5,6]:
        daytype = "weekend"

    return month, day, daytype, hour

matched_df_w_t = matched_df.copy()
matched_df_w_t[['month', 'day_of_week', 'daytype', 'hour_of_day']] = matched_df_w_t.apply(time_expand, axis=1, result_type="expand")


######### Extract metadata given matched edges and nodes ###########

vehicle_ids = matched_df_w_t[trip_veh_id_str].unique()
new_ids = {v_id:str(uuid.uuid4()) for v_id in vehicle_ids}
matched_df_w_t[trip_veh_id_str] = matched_df_w_t[trip_veh_id_str].map(new_ids)

matched_df_w_t.rename(columns={trip_veh_id_str: 'data_id'}, inplace=True)


#%%
matched_df_w_t.to_feather(input_path+"result_2.feather")
#%%
temp = matched_df_w_t.groupby(['data_id', 'way_id', 'month', 'day_of_week', 'daytype', 'hour_of_day']).agg({'travel_time_s': 'sum', 'distance_m': 'sum', 'distance_km':'sum'}).reset_index()

temp['speed_mps'] = temp['distance_m'] / temp['travel_time_s']
temp['speed_kmph'] = temp['distance_km'] / (temp['travel_time_s']/3600)

#%%
temp = temp.groupby(['way_id', 'month', 'day_of_week', 'daytype', 'hour_of_day']).agg({'travel_time_s': 'mean', 'speed_mps': 'mean', 'speed_kmph': 'mean'}).reset_index()
#%%
#%%
n_temp = matched_df_w_t.groupby(['data_id', 'node_id', 'month', 'day_of_week', 'daytype', 'hour_of_day']).agg({'travel_time_s': 'sum', 'distance_m': 'sum', 'distance_km':'sum'}).reset_index()
n_temp['speed_mps'] = n_temp['distance_m'] / n_temp['travel_time_s']
n_temp['speed_kmph'] = n_temp['distance_km'] / (n_temp['travel_time_s']/3600)

#%%
n_temp = n_temp.groupby(['node_id', 'month', 'day_of_week', 'daytype', 'hour_of_day']).agg({'travel_time_s': 'mean', 'speed_mps': 'mean', 'speed_kmph':'mean'}).reset_index()
#%%
# df1 = pd.read_feather(input_path+"result_1.feather")
# df2 = pd.read_feather(input_path+"result_2.feather")

# %%
# df1['distance_m'].sum() - df2["distance_m"].sum()
#%%
# df1['speed_kmph'].sum() - df2["speed_kmph"].sum()
#%%
# df1['travel_time_s'].sum() - df2["travel_time_s"].sum()
# %%

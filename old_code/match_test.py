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
from pathlib import Path

df = None
save = True
file_path = "~/websites/mapedia/media/top_10_percentage.csv"

if df is None:
    file_p = Path(file_path)
    extension = file_p.suffix
    if extension == '.csv':
        df = pd.read_csv(file_path)
    elif extension == '.parquet':
        df = pd.read_parquet(file_path)
    else:
        raise NotImplementedError("Not Implemented yet.")

print(df.head(1))
timestamp_str = 'timestamp'
lat_str = 'lat'
lon_str = 'long'
trip_veh_id_str = 'traj_id'
df[timestamp_str] = pd.to_datetime(df[timestamp_str])
df = df.sort_values(by=[trip_veh_id_str, timestamp_str])
# trip = df

######### Map match the trajectory to nodes and edges ###########
# Get the graph from the bounding box of the trajectory and project both to the same CRS
lat_col = df[lat_str]
long_col = df[lon_str]
n = max(lat_col)
s = min(lat_col)
e = max(long_col)
w = min(long_col)
network_type = "drive"
print(n, s, e, w)
# G = ox.graph_from_bbox((w, s, e, n), network_type=network_type, simplify=False, retain_all=True, truncate_by_edge=False)
G = ox.graph_from_bbox(n, s, e, w, network_type=network_type, simplify=False, retain_all=True, truncate_by_edge=False)
G_proj = ox.project_graph(G)
print("graph done")
#%%
from mappymatch.constructs.trace import Trace
from mappymatch.matchers.lcss.lcss import LCSSMatcher
from shapely.geometry import box
from mappymatch.utils.crs import LATLON_CRS, XY_CRS
from pyproj import Transformer
from shapely.ops import transform
from mappymatch.constructs.geofence import Geofence
from mappymatch.maps.nx.nx_map import NxMap, NetworkType


def process_traces(gdf):
    vechile_ids = sorted(gdf.traj_id.unique())

    print('Processing Traces for our input...!')
    start_time = time.time()
    list_of_traces = []
    for id in tqdm(vechile_ids):
        sub_df = gdf[gdf.traj_id == id]
        trace = Trace.from_geo_dataframe(frame=sub_df)
        list_of_traces.append(trace)
    end_time = time.time()
    print("Took ", end_time - start_time, " seconds")
    return list_of_traces, vechile_ids
def get_MBR_polygon(gdf, padding):
    """
    Create a GeoFence around the geometeries provided in the GeoPandas DataFrame
    Args:
        gdf: [GeoDataFrame] the GeoPandas DataFrame
        buffer_resolution: [Integer] the buffer around the geometries to create the fence
    """
    # Adding a buffer per each point in the GeoPandas Dataframe
    print('Calculating the Buffer Around Each Point (Parallel via GeoDask)...!')
    min_x, min_y, max_x, max_y = gdf.total_bounds
    if padding == -1: 
        range = max_x - min_x 
        padding = 0.5 * range
    return box(min_x-padding, min_y-padding, max_x+padding, max_y+padding)

def convert_polygon_crs(polygon, polygon_crs, target_crs):
    if polygon_crs == target_crs:
        return polygon
    project = Transformer.from_crs(
        polygon_crs, target_crs, always_xy=True
    ).transform
    return transform(project, polygon)

nprocesses = 1
padding = -1

gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_str], df[lat_str]), crs='EPSG:4326')
gdf_proj = gdf.to_crs(G_proj.graph['crs'])
list_of_traces, vehicle_ids = process_traces(gdf_proj)
geofence = get_MBR_polygon(gdf, padding)
# polygon = convert_polygon_crs(geofence, XY_CRS, LATLON_CRS)
# polygon = geofence

geofence = Geofence(crs=LATLON_CRS, geometry=geofence)
# geofence = Geofence(crs=XY_CRS, geometry=polygon)
road_network = NxMap.from_geofence(geofence,
                                   network_type=NetworkType.DRIVE)
# Add speed and travel time manually
matcher = LCSSMatcher(road_network)
matches = matcher.match_trace_batch(
    trace_batch = list_of_traces, 
    processes=nprocesses
)
print(matches)

#%%
# Match the trajectory points to the nearest nodes and edges
# edge_list = ox.nearest_edges(G_proj, long_col_proj, lat_col_proj, return_dist=True)
# node_list = ox.nearest_nodes(G_proj, long_col_proj, lat_col_proj, return_dist=True)
# Extract the OSM way IDs from the matched edges
way_ids = []  # Store OSM way IDs
edge_ids = []  # Store edge IDs
long_list = []
lat_list = []
node_list = []
for i, trace in enumerate(list_of_traces):
    matched_list_of_roads = matches[i]
    for j, road in enumerate(matched_list_of_roads.matches):
        point = (trace.coords[j].x, trace.coords[j].y)
        if road.road is None: 
            road_id = ox.nearest_edges(G_proj, point[0], point[1])
        else:
            road_id = (road.road.road_id.start, road.road.road_id.end, road.road.road_id.key)
        # u, v, key = edge  # Extract edge details
        osmid = road_network.g.edges[road_id].get('osmid', None)  # Get the OSM way ID
        if isinstance(osmid, list):  # Handle cases where multiple OSMIDs exist
            print(osmid)
            osmid = osmid[0]  # Take the first one (adjust logic as needed)
        long_list.append(point[0])
        lat_list.append(point[1])
        way_ids.append(osmid)
        edge_ids.append(str(road_id))
#%%
# Extract the OSM way IDs from the matched edges
way_ids = []  # Store OSM way IDs
edge_ids = []  # Store edge IDs

for edge in edge_list[0]:
    # u, v, key = edge  # Extract edge details
    osmid = G_proj.edges[edge].get('osmid', None)  # Get the OSM way ID
    if isinstance(osmid, list):  # Handle cases where multiple OSMIDs exist
        print(osmid)
        osmid = osmid[0]  # Take the first one (adjust logic as needed)
    way_ids.append(osmid)
    edge_ids.append(str(edge))

#%%
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

#%%
matched_df = df.join(map_matching_df, lsuffix='', rsuffix='_right')
matched_df.drop([c for c in matched_df.columns if '_right' in c], axis=1, inplace=True)
print("matching done")

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
print("extracting done")

#%%
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
        daytype = False
    elif day in [5,6]:
        daytype = True

    return month, day, daytype, hour

matched_df_w_t = matched_df.copy()
matched_df_w_t[['month', 'day_of_week', 'daytype', 'hour_of_day']] = matched_df_w_t.apply(time_expand, axis=1, result_type="expand")

#%%
######### Extract metadata given matched edges and nodes ###########

vehicle_ids = matched_df_w_t[trip_veh_id_str].unique()
new_ids = {v_id:str(uuid.uuid4()) for v_id in vehicle_ids}
matched_df_w_t[trip_veh_id_str] = matched_df_w_t[trip_veh_id_str].map(new_ids)

matched_df_w_t.rename(columns={trip_veh_id_str: 'data_id'}, inplace=True)

way_metadata = matched_df_w_t.groupby(['data_id', 'way_id', 'edge_id', 'month', 'day_of_week', 'daytype', 'hour_of_day']).agg({'travel_time_s': 'sum', 'distance_m': 'sum'}).reset_index()

# temp['speed_mps'] = temp['distance_m'] / temp['travel_time_s']
# temp['speed_kmph'] = temp['distance_km'] / (temp['travel_time_s']/3600)

#%%
# temp = temp.groupby(['way_id', 'month', 'day_of_week', 'daytype', 'hour_of_day']).agg({'travel_time_s': 'mean', 'speed_mps': 'mean', 'speed_kmph': 'mean'}).reset_index()
#%%
node_metadata = matched_df_w_t.groupby(['data_id', 'node_id', 'month', 'day_of_week', 'daytype', 'hour_of_day']).agg({'travel_time_s': 'sum', 'distance_m': 'sum'}).reset_index()
# n_temp['speed_mps'] = n_temp['distance_m'] / n_temp['travel_time_s']
# n_temp['speed_kmph'] = n_temp['distance_km'] / (n_temp['travel_time_s']/3600)

#%%
# n_temp = n_temp.groupby(['node_id', 'month', 'day_of_week', 'daytype', 'hour_of_day']).agg({'travel_time_s': 'mean', 'speed_mps': 'mean', 'speed_kmph':'mean'}).reset_index()
print("aggregating done")

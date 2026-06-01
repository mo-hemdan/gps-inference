# %%
import sys
sys.path.append('/home/spatialuser/websites/mapedia')
from modules import (
    DBHandler, 
    DBUpdater, 
    GPS_INFERENCE_SOURCE,
    NumpyNearestEdgeMatcher
)
import osmnx as ox
import numpy as np
import pandas as pd
from tqdm import tqdm
tqdm.pandas()
import geopandas as gpd
from utiles import get_timebin_index, add_signed_distance, heading_to_unit_vector
import itertools
from sklearn.metrics import accuracy_score, mean_absolute_percentage_error, mean_absolute_error

# %%
db_handler = DBHandler()
db_handler.connect_to_db()

db_updater = DBUpdater(db_handler)

min_lon, min_lat, max_lon, max_lat = 106.7483, -6.2517, 106.8344, -6.1740
G = db_handler.get_graph(
    min_lat= min_lat,
    max_lat= max_lat,
    min_lon= min_lon,
    max_lon= max_lon
)
# edges.set_index('id', inplace=True)
# edges.to_crs("EPSG:3857", inplace=True)

#%%
# ox.plot_graph(G)
points = db_handler.gps_points_from_bbox(min_lon, min_lat, max_lon, max_lat)
points.to_crs('EPSG:3857', inplace=True)

# %% Using the new matched
matcher = NumpyNearestEdgeMatcher(G)
points = matcher.match(points, advanced_matching=True)

# %% Incremental Trajectory Inference
edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
road_id_map = edges['id'].to_dict()
points['matched_road_id'] = points['matched_road_id'].apply(tuple).map(road_id_map)
matched_roads = points.matched_road_id.unique()
print(matched_roads)

# %% Begin the Incremental Inference process
class RoadMetadataInference:
    def __init__(self):
        self.nDays = 7
        self.nSeasons = 4
        self.nHours = 24
        pass
    
    def initialize_memStruct(self, matched_roads):
        TimeBins = self.nHours * self.nDays * self.nSeasons
        road_metadata_df = pd.DataFrame(
            index= matched_roads,
            columns=['v_max', 'v_min', 'd_left', 'd_right', 'n_forward', 'n_backward', 'mu_d', 'M_d', 'n_d', 'v_n', 'v_mu', 'v_M']
        )
        road_metadata_df['v_min'] = float("inf")
        road_metadata_df['v_max'] = float("-inf")
        road_metadata_df['d_left'] = float("inf")
        road_metadata_df['d_right'] = float("-inf")
        road_metadata_df['n_d'] = 0
        road_metadata_df['mu_d'] = 0.0
        road_metadata_df['M_d'] = 0.0
        road_metadata_df['n_forward'] = 0
        road_metadata_df['n_backward'] = 0
        road_metadata_df['v_n'] = [np.zeros(TimeBins) for _ in range(len(matched_roads))]
        road_metadata_df['v_mu'] = [np.zeros(TimeBins) for _ in range(len(matched_roads))]
        road_metadata_df['v_M'] = [np.zeros(TimeBins) for _ in range(len(matched_roads))]
        
        return road_metadata_df
    
    def estimate_metadata(self, points, road_metadata_df): #, matched_roads):
        # road_metadata_df = self.initialize_memStruct(matched_roads)
        
        road_to_idx_iloc = {idx: i for i, idx in enumerate(road_metadata_df.index.tolist())}
        points['matched_road_idx'] = points['matched_road_id'].map(road_to_idx_iloc)

        v_n = np.stack(road_metadata_df["v_n"].to_numpy())
        v_mu = np.stack(road_metadata_df["v_mu"].to_numpy())
        v_M = np.stack(road_metadata_df["v_M"].to_numpy())

        v_min = road_metadata_df["v_min"].to_numpy()
        v_max = road_metadata_df["v_max"].to_numpy()
        d_left = road_metadata_df["d_left"].to_numpy()
        d_right = road_metadata_df["d_right"].to_numpy()
        mu_d = road_metadata_df["mu_d"].to_numpy()
        M_d = road_metadata_df["M_d"].to_numpy()
        n_d = road_metadata_df["n_d"].to_numpy()
        n_forward = road_metadata_df["n_forward"].to_numpy()
        n_backward = road_metadata_df["n_backward"].to_numpy()

        for row in tqdm(points.itertuples(index=False), total=len(points)):

            r = row.matched_road_idx
            t = get_timebin_index(row.timestamp)

            speed = row.speed * 3.6
            d = row.signed_distance

            # scalar updates
            v_min[r] = min(v_min[r], speed)
            v_max[r] = max(v_max[r], speed)
            d_left[r] = min(d_left[r], d)
            d_right[r] = max(d_right[r], d)

            n_d[r] += 1
            delta_d = d - mu_d[r]
            mu_d[r] += delta_d / n_d[r]
            M_d[r] += delta_d * (d - mu_d[r])

            if row.r_p_sim > 90:
                n_backward[r] += 1
            else:
                n_forward[r] += 1

            # timebin updates
            v_n[r, t] += 1

            delta = speed - v_mu[r, t]
            v_mu[r, t] += delta / v_n[r, t]

            delta2 = speed - v_mu[r, t]
            v_M[r, t] += delta * delta2

        v_var = np.where(v_n > 1, v_M / (v_n - 1), 0.0)
        v_std = np.sqrt(v_var)

        std_d = np.sqrt(M_d / (n_d - 1))

        road_metadata_df["v_n"] = list(v_n)
        road_metadata_df["v_mu"] = list(v_mu)
        road_metadata_df["v_M"] = list(v_M)

        road_metadata_df["v_min"] = v_min
        road_metadata_df["v_max"] = v_max
        road_metadata_df["d_left"] = d_left
        road_metadata_df["d_right"] = d_right
        road_metadata_df["mu_d"] = mu_d
        road_metadata_df["M_d"] = M_d
        road_metadata_df["n_d"] = n_d
        road_metadata_df["n_forward"] = n_forward
        road_metadata_df["n_backward"] = n_backward

        road_metadata_df["std_d"] = std_d
        road_metadata_df["v_std"] = list(v_std)
        
        # Estimate some of the values
        road_metadata_df['max_speed'] = road_metadata_df['v_max']
        road_metadata_df.loc[road_metadata_df["max_speed"] <= 0, "max_speed"] = None
        road_metadata_df['max_speed_conf'] = 0.7
        road_metadata_df['max_speed_source'] = GPS_INFERENCE_SOURCE
        
        road_metadata_df['min_speed'] = road_metadata_df['v_min']
        road_metadata_df.loc[road_metadata_df["min_speed"] <= 0, "min_speed"] = None
        road_metadata_df['min_speed_conf'] = 0.7
        road_metadata_df['min_speed_source'] = GPS_INFERENCE_SOURCE
        
        road_metadata_df['width'] = self.estimate_width(road_metadata_df)
        road_metadata_df['width_conf'] = 0.7
        road_metadata_df['width_source'] = GPS_INFERENCE_SOURCE
        
        road_metadata_df['oneway'] = self.estimate_oneway(road_metadata_df)
        road_metadata_df['oneway_conf'] = 0.7
        road_metadata_df['oneway_source'] = GPS_INFERENCE_SOURCE
        
        
        temporal_attr = self.expand_temporal_arr(road_metadata_df)
        
        static_attr = road_metadata_df[[
            'max_speed', 'max_speed_conf', 'max_speed_source',
            'min_speed', 'min_speed_conf', 'min_speed_source',
            'width', 'width_conf', 'width_source',
            'oneway', 'oneway_conf', 'oneway_source'
            ]].copy()
        static_attr.index.name = None
        
        
        return static_attr, temporal_attr
    
    def expand_temporal_arr(self, road_metadata_df):
        season_list = list(range(self.nSeasons))
        day_list = list(range(self.nDays))
        hour_list = list(range(self.nHours))

        grid = list(itertools.product(season_list, day_list, hour_list))

        # IMPORTANT: grid length must match v_mu length
        print(len(grid), len(road_metadata_df["v_mu"].iloc[0]))

        rows = []

        for idx, row in tqdm(road_metadata_df.iterrows(), total=len(road_metadata_df), desc='Expanding'):
            vec = row["v_mu"]

            for (season, dow, hour), value in zip(grid, vec):
                if value!=0:
                    rows.append((idx, season, dow, hour, value))

        temporal_attr = pd.DataFrame(
            rows,
            columns=["matched_road_id", "season", "dayOfWeek", "hour", "avg_speed"]
        ).set_index(["matched_road_id", "season", "dayOfWeek", "`hour"])

        temporal_attr['avg_speed_conf'] = 0.7
        temporal_attr['avg_speed_source']= GPS_INFERENCE_SOURCE
        temporal_attr.index.name = None
        return temporal_attr
    
    def estimate_width(self, road_attributes, width_factor=4):
        return width_factor * road_attributes["M_d"]

    def estimate_oneway(self, road_attributes, error_percentage=0.05):
        max_number = np.maximum(road_attributes['n_forward'], road_attributes['n_backward'])
        min_number = np.minimum(road_attributes['n_forward'], road_attributes['n_backward'])
        r = min_number / max_number
        return  (r < error_percentage).astype(int)
        
        
    def nullify_empty_metadata(self, metadata_tbl):
        
        return
        

metadata_estimator = RoadMetadataInference()
road_metadata_df = metadata_estimator.initialize_memStruct(matched_roads)
static_attr, temporal_attr = metadata_estimator.estimate_metadata(points, road_metadata_df)

# %% Evaluation of Metadata
true_road_attributes = db_handler.roads_from_ids(matched_roads.tolist())
merged_static_attr = true_road_attributes[['oneway', 'max_speed', 'min_speed', 'width']].merge(
    static_attr[['oneway', 'max_speed', 'min_speed', 'width']],
    left_index=True,
    right_index=True,
    how="left",
    suffixes=("", "_pred")
)

# %% Metrics
tmp = merged_static_attr.dropna(subset=['oneway', 'oneway_pred'])
oneway_acc = accuracy_score(
    tmp['oneway'],
    tmp['oneway_pred']
)
tmp = merged_static_attr.dropna(subset=['max_speed', 'max_speed_pred'])
max_speed_err = mean_absolute_error(
    tmp['max_speed'],
    tmp['max_speed_pred']
)
# tmp = merged_static_attr.dropna(subset=['min_speed'])
# min_speed_err = mean_absolute_percentage_error(
#     tmp['min_speed'],
#     tmp['min_speed_pred']
# )
tmp = merged_static_attr.dropna(subset=['width', 'width_pred'])
width_err = mean_absolute_error(
    tmp['width'],
    tmp['width_pred']
)
print("Oneway Accuracy:", oneway_acc)
print("Max Speed Error:", max_speed_err)
# print("Min Speed Error:", min_speed_err)
print("Width Error:", width_err)



# %%

# %%
# gdf["road_geometry"] = gdf["road_geometry"].apply(lambda geom: geom.wkt)
# gdf.to_parquet("./data/matched_geom.parquet")
# road_metadata_df.to_parquet("./data/road_metadata.parquet")  
# gdf = gpd.read_parquet("./data/matched_geom.parquet")
# road_metadata_df = pd.read_parquet("./data/road_metadata.parquet")
# db_updater.update_database(static_attr=static_attr, temporal_attr=temporal_attr, static_cols=['max_speed', 'min_speed', 'oneway', 'width'])  

# %% static attribute accuracy



# %%
merged_static_attr['max_speed'].hist()
merged_static_attr['max_speed_pred'].hist()





# %% Let's visualize the map on map for points and road attributes
# edges = matcher.edges
edges.set_index('id', inplace=True)
complete_roads = edges.merge(
    merged_static_attr,
    left_index=True,
    right_index=True,
    how="left",
    suffixes=("_osrm", "")
)
complete_roads.to_crs("EPSG:4326", inplace=True)

# %%
points = points[['id', 'dataset', 'traj_id', 'order_id', 'timestamp', 'speed', 'angle',
       'accuracy', 'processed', 'matched_road_osm_id', 'geometry',
       'driving_mode', 'osname', 'matched_road_id', 'distance_to_matched_road',
       'road_angle', 'r_p_sim', 'road_length',
       'signed_distance', 'road_dir', 'matched_road_idx']]
points.set_index('id', inplace=True)
points.to_crs("EPSG:4326", inplace=True)

# %%
complete_roads.to_file("./vis_data/complete_roads.geojson", driver="GeoJSON")
points.sample(100000).to_file("./vis_data/points.geojson", driver="GeoJSON")

# %%
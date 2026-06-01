# %%
import sys
sys.path.append('/home/spatialuser/websites/mapedia')

from modules import DBHandler, DATASET_INDEX
# %% Evaluating the accuracy of the output map metadata
from modules import RoadAttrEstimator, DBHandler, NearestEdgeMatcher, DBUpdater
from modules import GPS_INFERENCE_SOURCE

db_handler = DBHandler()
db_updater = DBUpdater(db_handler)
db_handler.connect_to_db()
# Get the graph for Jakarta
# G = db_handler.get_graph(
#     min_lat= -6.3725962,
#     max_lat= -6.0785515,
#     min_lon= 106.686105,
#     max_lon= 106.9737509
# )
min_lon, min_lat, max_lon, max_lat = 106.7483, -6.2517, 106.8344, -6.1740

G = db_handler.get_graph(
    min_lat= min_lat,
    max_lat= max_lat,
    min_lon= min_lon,
    max_lon= max_lon
)

#%%
import osmnx as ox
ox.plot_graph(G)


# %%
# gdf = db_handler.get_gps_dataset(DATASET_INDEX['jakarta'])
gdf = db_handler.gps_points_from_bbox(min_lon, min_lat, max_lon, max_lat)
#%% Select a smaller subset 
# gdf_small = gdf.cx[min_lon:max_lon,  min_lat:max_lat]
# G_small = ox.truncate.truncate_graph_bbox(
#     G,
#     bbox=(min_lon, min_lat, max_lon, max_lat),
#     truncate_by_edge=True  # keeps edges that cross the boundary
# )

# %%
gdf.shape
gdf.to_crs('EPSG:3857', inplace=True)
# %%
from modules import NewNearestEdgeMatcher
matcher = NewNearestEdgeMatcher(G)
gdf = matcher.match(gdf, advanced_matching=True)

# %% Incremental Trajectory Inference
road_id_map = matcher.edges['id'].to_dict()
gdf['matched_road_id'] = gdf['matched_road_id'].apply(tuple).map(road_id_map)




matched_roads = gdf.matched_road_id.unique()

print(matched_roads)

# %%
import numpy as np
import pandas as pd

TimeBins = 24 * 7 * 4
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

# %%
road_metadata_df.index = pd.MultiIndex.from_tuples(
    road_metadata_df.index,
    names=["u", "v", "k"]
)

# %%


#%%

def get_timebin_index(ts):
    # Hour
    hour = ts.hour

    # Day of week (Monday = 0, Sunday = 6)
    day_of_week = ts.day_of_week
    # print(day_of_week)
    # Season
    def get_season(month):
        return 0 if month == 12 else month // 3

    season = get_season(ts.month)
    idx = season*7*24 + day_of_week*24 + hour
    return idx

from shapely.geometry import LineString, Point


# Incrementally loop over the GPS points
from tqdm import tqdm
tqdm.pandas()


# %%
def heading_to_unit_vector(heading_deg):
    theta = np.deg2rad(heading_deg)
    return np.sin(theta), np.cos(theta)

def add_signed_distance(gdf):
    def signed_distance(row):
        signed_d = 0.0
        road_dir = None

        point = row.geometry
        line = row.road_geometry
        heading = row.angle
        
        # 1. snap point to line
        s = line.project(point)
        eps = 0.5  # small distance to determine direction
        snapped = line.interpolate(s)

        # 2. unsigned distance
        d = point.distance(snapped)
        
        # vector from snapped point to actual point
        # 3. take first segment as direction
        x0, y0 = line.coords[0]
        x1, y1 = line.coords[1]
        # direction vector of line
        dx = x1 - x0
        dy = y1 - y0
        vx = point.x - snapped.x
        vy = point.y - snapped.y

        # 4. cross product (2D "z-component")
        cross = dx * vy - dy * vx  # determines sign

        # 5. signed distance
        if cross >= 0:
            signed_d = +d
        else:
            signed_d = -d

        s0 = max(0, s - eps)
        s1 = min(line.length, s + eps)
        p0 = line.interpolate(s0)
        p1 = line.interpolate(s1)
        dx = p1.x - p0.x
        dy = p1.y - p0.y
        norm = np.hypot(dx, dy)
        if norm == 0:
            tangent = None
        tangent = dx / norm, dy / norm

        hx, hy = heading_to_unit_vector(heading)
        cos_sim = hx * tangent[0] + hy * tangent[1]

        if abs(cos_sim) < 0.3:
            road_dir = 0
        elif cos_sim > 0:
            road_dir = +1
        else:
            road_dir = -1

        return signed_d, road_dir

    # ✅ THIS preserves the original index perfectly
    tqdm.pandas(desc="Adding signed distances and directions")
    gdf[["signed_distance", "road_dir"]] = (
        gdf.progress_apply(signed_distance, axis=1, result_type="expand")
    )
    return gdf


# %%
gdf = add_signed_distance(gdf)

# %%
gdf["road_geometry"] = gdf["road_geometry"].apply(lambda geom: geom.wkt)
gdf.to_parquet("./data/matched_geom.parquet")
#%%
road_metadata_df.to_parquet("./data/road_metadata.parquet")  

# %%
import geopandas as gpd
import pandas as pd

gdf = gpd.read_parquet("./data/matched_geom.parquet")
road_metadata_df = pd.read_parquet("./data/road_metadata.parquet")

# %%

road_metadata_df = road_metadata_df.reset_index()
road_metadata_df_roads = road_metadata_df[['u', 'v', 'k']].apply(tuple, axis=1).map(road_id_map)
road_metadata_df.index = road_metadata_df_roads
road_to_idx = {
    (row.u, row.v, row.k): idx
    for idx, row in road_metadata_df.iterrows()
}
road_to_idx_iloc = {
    idx: row.index
    for idx, row in road_metadata_df.iterrows()
}

gdf['matched_road_id'] = gdf['matched_road_id']#.apply(tuple).map(road_to_idx)
gdf['matched_road_idx'] = gdf['matched_road_id'].map(road_to_idx_iloc)

road_metadata_df.drop(columns=['u', 'v', 'k'], inplace=True)

# %%
from tqdm import tqdm
import numpy as np

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

for row in tqdm(gdf.itertuples(index=False), total=len(gdf)):

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


# %%
road_metadata_df.head()



#%%
road_metadata_df['maxspeed'] = road_metadata_df['v_max']
road_metadata_df['minspeed'] = road_metadata_df['v_min']

def estimate_width(road_attributes, width_factor=4):
    
    road_attributes['width'] = width_factor * road_attributes["M_d"]
    return road_attributes

def estimate_oneway(road_attributes, error_percentage=0.05):
    max_number = np.maximum(road_attributes['n_forward'], road_attributes['n_backward'])
    min_number = np.minimum(road_attributes['n_forward'], road_attributes['n_backward'])
    r = min_number / max_number
    
    road_attributes['oneway'] =  (r < error_percentage)
    return road_attributes
    

road_metadata_df = estimate_width(road_metadata_df)
road_metadata_df = estimate_oneway(road_metadata_df)

# %% Converting the temporal thing
static_attr = (
    road_metadata_df[
        ['maxspeed', 'minspeed', 'oneway', 'width']
    ]
    .rename(columns={
        'minspeed': 'min_speed',
        'maxspeed': 'max_speed'
    })
)
static_attr['max_speed_conf'] = 0.7
static_attr['min_speed_conf'] = 0.7
static_attr['oneway_conf'] = 0.7
static_attr['width_conf'] = 0.7

static_attr['max_speed_source'] = GPS_INFERENCE_SOURCE
static_attr['min_speed_source'] = GPS_INFERENCE_SOURCE
static_attr['oneway_source'] = GPS_INFERENCE_SOURCE
static_attr['width_source'] = GPS_INFERENCE_SOURCE
static_attr.index.name = None

static_attr['oneway'] = static_attr['oneway'].astype(int)
# %%
import itertools
import pandas as pd
import numpy as np

season_list = sorted(range(4))   # or fixed order if known
day_list = list(range(7))
hour_list = list(range(24))

grid = list(itertools.product(season_list, day_list, hour_list))

# IMPORTANT: grid length must match v_mu length
print(len(grid), len(road_metadata_df["v_mu"].iloc[0]))

#%%
rows = []

for idx, row in road_metadata_df.iterrows():
    vec = row["v_mu"]

    for (season, dow, hour), value in zip(grid, vec):
        if value!=0:
            rows.append((idx, season, dow, hour, value))

temporal_attr = pd.DataFrame(
    rows,
    columns=["matched_road_id", "season", "dayOfWeek", "hour", "avg_speed"]
).set_index(["matched_road_id", "season", "dayOfWeek", "hour"])

temporal_attr['avg_speed_conf'] = 0.7
temporal_attr['avg_speed_source']= GPS_INFERENCE_SOURCE
temporal_attr.index.name = None

# %%
# TODO: To add the
# db_updater.update_database(static_attr=static_attr, temporal_attr=temporal_attr, static_cols=['max_speed', 'min_speed', 'oneway', 'width'])  

# %%

# %% Evaluation of output metadata
# roads = static_attr.index.tolist()
# true_road_attributes = db_handler.roads_from_ids(roads)
# %% Evaluating the output map metadata
merged_static_attr = true_road_attributes[['oneway', 'max_speed', 'min_speed', 'width']].merge(
    static_attr[['oneway', 'max_speed', 'min_speed', 'width']],
    left_index=True,
    right_index=True,
    how="left",
    suffixes=("", "_pred")
)


# %% static attribute accuracy
from sklearn.metrics import accuracy_score, mean_absolute_percentage_error, mean_absolute_error

tmp = merged_static_attr.dropna(subset=['oneway'])
oneway_acc = accuracy_score(
    tmp['oneway'],
    tmp['oneway_pred']
)
tmp = merged_static_attr.dropna(subset=['max_speed'])
max_speed_err = mean_absolute_error(
    tmp['max_speed'],
    tmp['max_speed_pred']
)
# tmp = merged_static_attr.dropna(subset=['min_speed'])
# min_speed_err = mean_absolute_percentage_error(
#     tmp['min_speed'],
#     tmp['min_speed_pred']
# )
tmp = merged_static_attr.dropna(subset=['width'])
width_err = mean_absolute_error(
    tmp['width'],
    tmp['width_pred']
)
print("Oneway Accuracy:", oneway_acc)
print("Max Speed Error:", max_speed_err)
# print("Min Speed Error:", min_speed_err)
print("Width Error:", width_err)

# %%
merged_static_attr['max_speed'].hist()
merged_static_attr['max_speed_pred'].hist()





# %% Let's visualize the map on map for points and road attributes
edges = matcher.edges
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
points = gdf[['id', 'dataset', 'traj_id', 'order_id', 'timestamp', 'speed', 'angle',
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
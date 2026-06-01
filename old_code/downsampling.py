# %%
import pandas as pd

df = pd.read_csv('fmm/gps_data/jakarta/trj_id.csv', sep=';')
df.head()
# %%
from shapely import wkt
from geopy.distance import geodesic
from shapely.geometry import Point, LineString
import requests
# Suppose df is your dataframe
# Columns: ['id', 'geom', 'timestamp']
df = df[~df.geom.isna()]
df['geom'] = df['geom'].apply(wkt.loads)  # Convert WKT to LineString

# # %%
# i = 0
# for g in df['geom']:
#     print('i ', i)
#     wkt.loads(g)
#     i +=1 
# %%

# Example function to map-match a LINESTRING using OSRM
def map_match_linestring(line, osrm_url="http://127.0.0.1:5000"):
    """
    line: shapely LineString
    Returns: OSRM response JSON
    """
    coords_str = ";".join(f"{x},{y}" for x, y in line.coords)
    url = f"{osrm_url}/match/v1/driving/{coords_str}"
    params = {
        "geometries": "geojson",
        "overview": "full",
        "steps": "true"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise RuntimeError(f"OSRM request failed: {response.status_code} {response.text}")


# Function to downsample points by distance
SAMPLING_DIST = 100
def downsample_points(coords, timestamps, min_distance_m):
    """
    coords: list of (lon, lat)
    timestamps: list of corresponding timestamps
    Returns: filtered coords and timestamps
    """
    if not coords:
        return [], []

    filtered_coords = [coords[0]]
    filtered_timestamps = [timestamps[0]]
    last_point = coords[0]

    for point, ts in zip(coords[1:], timestamps[1:]):
        if geodesic((last_point[1], last_point[0]), (point[1], point[0])).meters >= min_distance_m:
            filtered_coords.append(point)
            filtered_timestamps.append(ts)
            last_point = point

    return filtered_coords, filtered_timestamps

total_points, reduced_points = 0, 0
removed_trajs = 0

# %%
# Process each trajectory
from tqdm import tqdm 
for idx, row in tqdm(df.iterrows(), total=len(df), desc='Matching Trajectories'):
    line = row['geom']
    timestamps = row['timestamp']
    l_p = len(timestamps)

    # Downsample points
    coords = list(line.coords)
    filtered_coords, filtered_timestamps = downsample_points(coords, timestamps, min_distance_m=SAMPLING_DIST)

    r_p = len(filtered_timestamps)
    # print('Reduced Traj ', idx, ' from ', l_p, ' to ', r_p)

    # Create new LineString
    if len(filtered_timestamps) < 2:
        removed_trajs += 1
        df.at[idx, 'geom'] = None
        df.at[idx, 'timestamp'] = None
        continue
    
    filtered_line = LineString(filtered_coords)
    total_points += l_p
    reduced_points += r_p

    # Optional: Map-match with OSRM
    try:
        result = map_match_linestring(filtered_line)
        # print(f"Trajectory {row['id']} matched with confidence {result['matchings'][0]['confidence']}")
    except RuntimeError as e:
        print(f"Error matching trajectory {row['id']}: {e}")

    # Update dataframe if you want
    df.at[idx, 'geom'] = filtered_line
    df.at[idx, 'timestamp'] = filtered_timestamps

print('Reduced total Trajectory Points from ', l_p, ' to ', r_p)
print('Removed Trajectories: ', removed_trajs)
# %%
df = df[~df.geom.isna()]
# %%
df.to_csv('fmm/gps_data/jakarta/trj_id_sampled.csv', sep=';', index=False)
# %%

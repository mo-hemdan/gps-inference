# %%
#%%
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor



# from tqdm.notebook import tqdm
print('Getting roads and edges')
edge_geoms = edges.geometry
tree = edge_geoms.sindex
tqdm.pandas()

# Split the GeoDataFrame into batches
# batch_size=1000
# batches = [gdf[i:i+batch_size] for i in range(0, len(gdf), batch_size)]
# %%
import numpy as np
from scipy.spatial.distance import cdist
import psutil
import os
# original_index = gdf.index

def find_nearest_edge_and_distance_batch(points_batch):
    # Prepare results
    print(f"[Process ID]:{os.getpid()} Matching Batch..")
    matched_road_ids = []
    distances = []
    road_geometries = []

    for idx, point in points_batch.iterrows():        
        # Find the nearest edge using spatial index
        nearest_idx, nearest_d = tree.nearest(point.geometry, return_distance=True)
        nearest_idx = nearest_idx[1][0]
        nearest_edge = edges.iloc[nearest_idx]
        nearest_d = nearest_d[0]
        
        # Append results and original index
        matched_road_ids.append(nearest_edge.name)
        distances.append(nearest_d)
        road_geometries.append(nearest_edge.geometry)
        # indices.append(original_index[idx])  # Preserve the original index
    
    # Return results as a DataFrame, keeping the original index
    return pd.DataFrame({
        'matched_road_id': matched_road_ids,
        'distance_to_matched_road': distances,
        'road_geometry': road_geometries
    }, index=points_batch.index)

# Create a function to handle batching and parallelization
def process_with_batches(gdf_points, edges, tree, batch_size=50000):
    # Split the GeoDataFrame into batches
    batches = [gdf_points.iloc[i:i+batch_size] for i in range(0, len(gdf_points), batch_size)]
    print(f"Head [Process ID]:{os.getpid()} Number of Lists = {len(batches)}")

    with ProcessPoolExecutor(max_workers=psutil.cpu_count(logical=False) - 1) as executor:
        results = list(executor.map(find_nearest_edge_and_distance_batch, batches))
    
    # Combine results, preserving the original index
    return pd.concat(results, ignore_index=False)


results_df = process_with_batches(gdf, edges, tree)
gdf[['matched_road_id', 'distance_to_matched_road', 'road_geometry']] = results_df

# print('processing')
# gdf[['matched_road_id', 'distance_to_matched_road', 'road_geometry']] = gdf['geometry'].progress_apply(find_nearest_edge_and_distance)

# %%

# Snapping the points to the road network
def snap_point_to_nearest_edge(point):
    point_geom  = point.geometry
    edge_geom = point.road_geometry
    snapped_point = edge_geom.interpolate(edge_geom.project(point_geom))
    return snapped_point

gdf['snapped_geometry'] = gdf.progress_apply(snap_point_to_nearest_edge, axis=1)
# %%
gdf['geometry'] = gdf['snapped_geometry']
gdf.drop(columns=['snapped_geometry', 'distance_to_matched_road'], inplace=True)

#%%
print('saving') 
gdf['road_geometry'] = gdf['road_geometry'].apply(lambda geom: geom.wkt)
gdf.to_parquet('city_Singapore_pro/matched_geom.parquet', compression='snappy')
print(gdf.head())

# %%

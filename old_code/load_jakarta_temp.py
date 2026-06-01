# %%
import pandas as pd
import geopandas as gpd
import os
from modules.MetadataInference.EditedAnaMetadataInference import EditedAnaMetadataInference
from modules.Preprocessor.StorageManager import StorageManager

file_path = 'media/GPSTraj/top_10_percentage.csv'

TrajInfer = EditedAnaMetadataInference()
    
# Load the trajectory data
# input_path = "/project/cs-dmlab/areeg/Metadata/metadata_inference/data/"
# file = "top_10_percentage.csv.csv"
file_type = "csv"
df = TrajInfer.read_file(file_path, file_type, None)
if file_type == "csv":
    df = pd.read_csv(file_path, compression=None)
elif file_type == "parquet":
    df = pd.read_parquet(file_path)
elif file_type == "feather":
    df = pd.read_feather(file_path)
elif file_type == "json":
    df = pd.read_json(file_path)
else:
    raise NotImplementedError("This extension is not implemented")
df.rename(columns={
    'timestamp': 'timestamp',
    'latitude': 'latitude',
    'longitude': 'longitude',
    'trip_id': 'traj_id'
}, inplace=True)
timestamp_str = 'timestamp'
lat_str = 'latitude'
lon_str = 'longitude'
trip_veh_id_str = 'traj_id'

df[timestamp_str] = pd.to_datetime(df[timestamp_str])
df = df.sort_values(by=[trip_veh_id_str, timestamp_str])

print(df.head(1))
# trip = df

######### Map match the trajectory to nodes and edges ###########

matched_df = TrajInfer.map_match(df, lat_str, lon_str)
print("matching done")

#%%
########## Extract metadata directly from the trajectory ###########
# Calculate the travel time, distance, and speed between consecutive points

matched_df = TrajInfer.extract_detailed_metadata(matched_df, trip_veh_id_str, timestamp_str, lat_str, lon_str)
print("extracting done")

#%%
matched_df_w_t = TrajInfer.TIME_agg(matched_df, timestamp_str)
print("time expanded")

#%%
######### Extract metadata given matched edges and nodes ###########
way_metadata, node_metadata = TrajInfer.group_extracted_metadata(matched_df_w_t, trip_veh_id_str)

print("aggregating done")

print(way_metadata.head())
print(node_metadata.head())
# %%

import pandas as pd
import geopandas as gpd
import os
from modules.MetadataInference.EditedAnaMetadataInference_old import EditedAnaMetadataInference
from modules.Preprocessor.StorageManager import StorageManager

    
df = pd.read_csv('media/GPSTraj/top_10_percentage.csv')
df.rename(columns={
        'timestamp': 'timestamp',
        'lat': 'lat',
        'long': 'long',
        'trj_id': 'traj_id'
}, inplace=True)
print(df.head())

TrajInfer = EditedAnaMetadataInference()
    

metada_edges, metadata_nodes = TrajInfer.extract_metadata(file_path='media/GPSTraj/top_10_percentage.csv', file_type="csv")

print(metada_edges.head())
print(metadata_nodes.head())
# %%
import pandas as pd

df = pd.read_parquet('data/Jakarta_subset.parquet')
df = pd.read_parquet('data/Jakarta_subset.parquet')

df = pd.read_parquet('data/Jakarta_subset.parquet')
df.rename(columns={
            'timestamp': 'pingtimestamp',
            'lat': 'rawlat',
            'lon': 'rawlng',
            'vehicule_id': 'trj_id'
        }, inplace=True)
df.to_parquet('data/Jakarta_subset.parquet')
# %%

import pandas as pd
import geopandas as gpd
import os
from EditedAnaMetadataInference import EditedAnaMetadataInference
# from ..modules.Preprocessor.StorageManager import StorageManager



TrajInfer = EditedAnaMetadataInference()
    

metada_edges, metadata_nodes = TrajInfer.extract_metadata(file_path='data/Jakarta_subset.parquet', file_type='parquet')

print(metada_edges.head())

# sm = StorageManager()
# sm.connect_to_db(
#     ip='cs-u-spatial-406.cs.umn.edu',
#     port='5432',
#     db_name='gis',
#     username='gis',
#     password='gis'
#     )

# sm.insert_metadata_into_db(metada_edges, metadata_nodes)

# print(f'Finished Inserting {i} into metadata database')
    
# %%

# %%

import pandas as pd
import geopandas as gpd
import os
from AnaTrajectoryMetadataInference import AnaTrajectoryMetadataInference



TrajInfer = AnaTrajectoryMetadataInference(constants_path='constants.json')
    
TrajInfer.set_dataset('data/Jakarta_subset3.parquet')
TrajInfer.extract_metadata(save=True)

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

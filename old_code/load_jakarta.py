import pandas as pd
import geopandas as gpd
import os
from modules.MetadataInference.EditedAnaMetadataInference import EditedAnaMetadataInference
from modules.Preprocessor.StorageManager import StorageManager

files = os.listdir('datasets/city=Jakarta')

for i, file in enumerate(files):
    df = pd.read_parquet('datasets/city=Jakarta/' + file)
    df.rename(columns={
          'pingtimestamp': 'timestamp',
          'rawlat': 'lat',
          'rawlng': 'long',
          'trj_id': 'traj_id'
    }, inplace=True)
    print(df.head())

    TrajInfer = EditedAnaMetadataInference()
        

    metada_edges, metadata_nodes = TrajInfer.extract_metadata(file_path='datasets/city=Jakarta/' + file, file_type='parquet')
    
    print(metada_edges.head())

    sm = StorageManager()
    sm.connect_to_db(
        ip='cs-u-spatial-406.cs.umn.edu',
        port='5432',
        db_name='gis',
        username='gis',
        password='gis'
        )
    
    sm.insert_metadata_into_db(metada_edges, metadata_nodes)
    
    print(f'Finished Inserting {i} into metadata database')
        
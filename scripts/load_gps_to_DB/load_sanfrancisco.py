#%%
import pandas as pd
from pathlib import Path
from tqdm import tqdm

DATA_DIR = Path("/mnt/fastssd/mapedia_datasets/sfmta_parquet")
from modules.gps_inference.data_loader.DatasetLoader import DatasetLoader
from modules.db_handler.DBHandler import DBHandler 

from mapmatcher.NearestEdgeMatcher import NearestEdgeMatcher
loader = DatasetLoader()
db_handler = DBHandler()
db_handler.connect_to_db()

colnames = {
    'lng': 'loc_x',
    'lat': 'loc_y',
    'speed': 'average_speed',
    'angle': 'heading',
    'timestamp': 'vehicle_position_date_time',
    'traj_id': 'vehicle_id',
}

conf = {
    'crs': 'EPSG:4326', # TODO: check this
    'dataset': 2
}

# 0 for Jakarta
# 1 for Singapore
# 2 SF 
file_type = 'parquet'
batch_size=10_000

for file in DATA_DIR.iterdir():
    print('Processing file: ', file)
    df = pd.read_parquet(file)

    print(f'Read {len(df)} points')

    df["vehicle_id"] = df["vehicle_id"].astype("int64")
    df["loc_x"] = pd.to_numeric(df["loc_x"], errors="coerce")
    df["loc_y"] = pd.to_numeric(df["loc_y"], errors="coerce")
    df["vehicle_position_date_time"] = pd.to_datetime(
        df["vehicle_position_date_time"],
        errors="coerce"
    )
    
    df = df.dropna(subset=["vehicle_id", "loc_x", "loc_y", "vehicle_position_date_time"])

    print(f'Kept only {len(df)} points')

    df = df[(df['loc_x'] != 0) & (df['loc_y'] != 0)]

    print(f'Removed Zero locations: {len(df)} points')

    print(f'Adjusting format')
    df = loader.adjust_format(df, colnames, conf)
    print(f'Creating GeoDataFrame')
    gdf = loader.create_gdf(df)
    print(f'Preparing for PostGIS')
    gdf = loader.prepare_for_postgis(gdf)

    minx, miny, maxx, maxy = gdf.total_bounds

    
    edges = db_handler.roads_from_bbox(minx, miny, maxx, maxy)
    
    mapmatcher = NearestEdgeMatcher(edges)
    gdf.to_crs('EPSG:3857', inplace=True)
    gdf = mapmatcher.match(gdf, advanced_matching=False)
    gdf.to_crs('EPSG:4326', inplace=True)

    print(f'Connecting to PostGIS')
    conn = loader.connect_to_postgis()

    gdf.drop(columns=['road_geometry', 'distance_to_matched_road'], inplace=True)
    gdf.rename(columns={'matched_road_id': 'matched_road_osm_id'}, inplace=True)

    # conn.rollback()
    print(f'Copying GeoDataFrame in batches')
    loader.copy_geodataframe_in_batches(gdf, "gps_points", conn, batch_size=batch_size)
    print(f'Loading Completed Successfully!')
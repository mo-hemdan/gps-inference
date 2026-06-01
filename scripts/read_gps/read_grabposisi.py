# %%
import pandas as pd
import geopandas as gpd

CITY ='Jakarta'
df = pd.read_parquet(f'city={CITY}')
df = df.rename(columns={"trj_id": "vehicule_id", "rawlat": "lat", "rawlng": "lon", "pingtimestamp": "timestamp", "bearing": "angle"})
df = df.sort_values(by=['vehicule_id', 'timestamp'])
df = df.reset_index()
df.drop(columns=['index'], inplace=True)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
gdf.to_crs(crs=3857, inplace=True) 
gdf.to_parquet(f'city={CITY}/sorted_geom.parquet', index=True, compression="gzip", engine="pyarrow")
# %%
CITY = 'Singapore'
df = pd.read_parquet(f'city={CITY}')
df = df.rename(columns={"trj_id": "vehicule_id", "rawlat": "lat", "rawlng": "lon", "pingtimestamp": "timestamp", "bearing": "angle"})
df = df.sort_values(by=['vehicule_id', 'timestamp'])
df = df.reset_index()
df.drop(columns=['index'], inplace=True)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
gdf.to_crs(crs=3857, inplace=True) 
gdf.to_parquet(f'city={CITY}/sorted_geom.parquet', index=True, compression="gzip", engine="pyarrow")
# %%

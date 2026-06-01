import pandas as pd
import geopandas as gpd

from pyproj import CRS
LATLON_CRS = CRS(4326)
XY_CRS = CRS(3857)

df = pd.read_parquet('data/city=Jakarta.parquet')
df = df.rename(columns={"trj_id": "vehicule_id", "rawlat": "lat", "rawlng": "lon", "pingtimestamp": "timestamp", "bearing": "angle"})
df = df.sort_values(by=['vehicule_id', 'timestamp'])
df = df.reset_index()
df.drop(columns=['index'], inplace=True)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
gdf.to_crs(crs=XY_CRS, inplace=True) 

gdf.to_parquet('data/Jakarta_sorted.parquet', index=True, compression="gzip", engine="pyarrow")
# by the way the data is in CRS 3857
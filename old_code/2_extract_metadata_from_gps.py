# %%
import pandas as pd

import geopandas as gpd

# %%
gdf = gpd.read_parquet('data/matched_geom.parquet')
print(gdf.head())
# %%
gdf['matched_road_id'] = gdf['matched_road_id'].apply(tuple)

gdf_speed = gdf.groupby('matched_road_id')['speed'].agg(['mean', 'min', 'max'])
gdf_speed.head()
# %%

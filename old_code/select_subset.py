#%%
import pandas as pd
import geopandas as gpd

from pyproj import CRS, Transformer

LATLON_CRS = CRS(4326)
XY_CRS = CRS(3857)

df = pd.read_parquet('data/Jakarta_sorted.parquet')
#%%
# Rectangle in lon/lat
# Rectangle in lon/lat (smaller range)
center_lon = (106.6714 + 106.8843) / 2  # 106.77785
center_lat = (-6.3122 + -6.1907) / 2    # -6.25145

# Choose a smaller half-width/height (in degrees)
half_width = 0.04   # adjust as needed
half_height = 0.04  # adjust as needed

left = center_lon - half_width
right = center_lon + half_width
bottom = center_lat - half_height
top = center_lat + half_height

# Convert bounds to 3857
transformer = Transformer.from_crs(LATLON_CRS, XY_CRS, always_xy=True)
x_min, y_min = transformer.transform(left, bottom)
x_max, y_max = transformer.transform(right, top)

# Filter DataFrame
# subset = df[
#     (df['lon'] >= left) & (df['lon'] <= right) &
#     (df['lat'] >= bottom) & (df['lat'] <= top)
# ]

subset  = df

# %%
subset.drop(columns=['geometry', 'point_id'], inplace=True)
subset.shape
# %%

subset.rename(columns={
            'timestamp': 'pingtimestamp',
            'lat': 'rawlat',
            'lon': 'rawlng',
            'vehicule_id': 'trj_id'
        }, inplace=True)
subset = subset.copy()
subset.to_parquet('data/Jakarta_subset3.parquet')
# %%

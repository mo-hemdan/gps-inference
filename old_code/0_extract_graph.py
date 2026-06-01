# %%
import psycopg2
import geopandas as gpd
import pandas as pd
from shapely import wkb


# Get the points dataset
points_df = pd.read_parquet('~/websites/mapedia/datasets/city=Jakarta')
points_df.head()

# %%
# Get boundary of points
min_lat = points_df['rawlat'].min()
max_lat = points_df['rawlat'].max()
min_lon = points_df['rawlng'].min()
max_lon = points_df['rawlng'].max()

# %%
SRID = 4326

# Connect to PostGIS
conn = psycopg2.connect(
    dbname="gis",
    user="gis",
    password="gis",
    host="cs-u-spatial-406",
    port="5432"
)

# Create cursor
cur = conn.cursor()

# Query roads with WKB geometries (make sure SRID is compatible with your region)
sql = f"""
SELECT osm_id, ST_AsBinary(geometry) as geometry
FROM roads
WHERE ST_Intersects(
    geometry,
    ST_MakeEnvelope(
        {min_lon},
        {min_lat},
        {max_lon},
        {max_lat},
        {SRID}
    )
);
"""

cur.execute(sql)
rows = cur.fetchall()

# Close cursor
cur.close()
conn.close()

# %%
# Convert rows to DataFrame
ids, geoms = zip(*rows)
df = pd.DataFrame({'osm_id': ids})

# Convert geometries from WKB to shapely LineStrings
df['geometry'] = [wkb.loads(bytes(g)) for g in geoms]

# Create GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')  # change SRID if needed

# %%

gdf.to_parquet('data/jakarta_roads.parquet', index=False)
# %%

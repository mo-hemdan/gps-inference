# %% (Required if you import modules from outside the folder)
import sys
sys.path.append('/home/spatialuser/websites/mapedia')
from modules import RoadAttrEstimator, DBHandler, NearestEdgeMatcher, DBUpdater
import math

db_handler = DBHandler()
db_handler.connect_to_db()


# original bbox
minx, miny, maxx, maxy = (
    106.7989,  # min lon
    -6.1675,   # min lat
    106.8195,  # max lon
    -6.1574    # max lat
)
minx, miny, maxx, maxy = (
    106.8030,  # min lon
    -6.1655,   # min lat
    106.8150,  # max lon
    -6.1595    # max lat
)
# # center latitude
# center_lat = (miny + maxy) / 2

# # km expansion
# km = 50

# # degree offsets
# lat_offset = km / 111.32
# lon_offset = km / (111.32 * math.cos(math.radians(center_lat)))

# expanded_bbox = (
#     minx - lon_offset,
#     miny - lat_offset,
#     maxx + lon_offset,
#     maxy + lat_offset,
# )

# minx, miny, maxx, maxy = (
#     106.7086,
#     -6.2573,
#     106.9098,
#     -6.0676
# )
# %%

gdf = db_handler.gps_points_from_bbox(minx, miny, maxx, maxy)
edges = db_handler.roads_from_bbox(minx, miny, maxx, maxy)

# %% Matching the data to the road network
gdf.to_crs(epsg=3857, inplace=True)
mapmatcher = NearestEdgeMatcher(edges)
gdf = mapmatcher.match(gdf, advanced_matching=False)
gdf.to_crs(epsg=4326, inplace=True)

# %% 
attr_estimator = RoadAttrEstimator()
print('Estimating road attributes...')
temporal_attr, static_attr = attr_estimator.estimate(gdf)
print('All AttributesEstimation done.')

static_attr.index.name = None
temporal_attr.index.name = None

print(temporal_attr, static_attr)
# %%
db_updater = DBUpdater(db_handler)
db_updater.update_database(static_attr=static_attr, temporal_attr=temporal_attr)
# %%

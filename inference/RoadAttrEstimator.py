from .LanesAndWidthEstimator import LanesAndWidthEstimator
from .SpeedEstimator import SpeedEstimator
from .OnewayEstimator import OnewayEstimator
from .RoadTypeEstimator import RoadTypeEstimator
import pandas as pd
import numpy as np
from tqdm import tqdm
tqdm.pandas()

# Extractable Road Attributes are:
# 1. Average Speed per temporal category (season, dayofweek, hour)
# 2. Number of Lanes (using GMM on signed distances)
# 3. Road Width (using percentiles on signed distances)
# 4. Max Speed Limit
# 5. Min Speed Limit
# 6. Oneway or not (can be fetched from road data in DB)
# Note: Other attributes like road type, oneway, etc. can be fetched directly from the road data in the DB
def heading_to_unit_vector(heading_deg):
    theta = np.deg2rad(heading_deg)
    return np.sin(theta), np.cos(theta)

class RoadAttrEstimator:
    def __init__(self):
        '''
        Extractor for road attributes from GPS data
        Assumes that the GPS points have been map-matched to roads
        
        :param self: Description
        '''
        self.lanes_and_width_estimator = LanesAndWidthEstimator()
        self.speed_estimator = SpeedEstimator()
        self.oneway_estimator = OnewayEstimator()
        self.road_type_estimator = RoadTypeEstimator()
        pass
    
    def estimate(self, points):

        print('Adding timezones and signed distances...')
        points = self.add_timezones(points)
        points = self.add_signed_distance(points)

        print("Grouping points per road and timezone...")
        points_per_road = points.groupby('matched_road_id')
        points_per_timezone = points.groupby(['matched_road_id', 'season', 'dayOfWeek', 'hour'])

        print("Estimating lanes, and width ...")
        lanes_and_width = self.lanes_and_width_estimator.estimate(points_per_road)
        print("Estimating speed ...")
        avg_speed, speed_limits = self.speed_estimator.estimate(points_per_timezone, points_per_road)
        print("Estimating oneway ...")
        oneway = self.oneway_estimator.estimate(points_per_road)
        print("Estimating road type ...")
        road_type = self.road_type_estimator.estimate(points_per_road)
        
        print("Combining all attributes...")
        static_attr = pd.concat([lanes_and_width, speed_limits, oneway, road_type], axis=1)
        temporal_attr = avg_speed
        return temporal_attr, static_attr
    
    def add_timezones(self, gdf): # we need the timestamp to be in the timestamp type
        gdf['season'] = (gdf['timestamp'].dt.month % 12) // 3
        gdf['dayOfWeek'] = gdf['timestamp'].dt.dayofweek
        gdf['hour'] = gdf['timestamp'].dt.hour
        return gdf

    def add_signed_distance(self, gdf):
        def signed_distance(row):
            signed_d = 0.0
            road_dir = None

            point = row.geometry
            line = row.road_geometry
            heading = row.angle
            
            # 1. snap point to line
            s = line.project(point)
            eps = 0.5  # small distance to determine direction
            snapped = line.interpolate(s)

            # 2. unsigned distance
            d = point.distance(snapped)
            
            # vector from snapped point to actual point
            # 3. take first segment as direction
            x0, y0 = line.coords[0]
            x1, y1 = line.coords[1]
            # direction vector of line
            dx = x1 - x0
            dy = y1 - y0
            vx = point.x - snapped.x
            vy = point.y - snapped.y

            # 4. cross product (2D "z-component")
            cross = dx * vy - dy * vx  # determines sign

            # 5. signed distance
            if cross >= 0:
                signed_d = +d
            else:
                signed_d = -d

            s0 = max(0, s - eps)
            s1 = min(line.length, s + eps)
            p0 = line.interpolate(s0)
            p1 = line.interpolate(s1)
            dx = p1.x - p0.x
            dy = p1.y - p0.y
            norm = np.hypot(dx, dy)
            if norm == 0:
                tangent = None
            tangent = dx / norm, dy / norm

            hx, hy = heading_to_unit_vector(heading)
            cos_sim = hx * tangent[0] + hy * tangent[1]

            if abs(cos_sim) < 0.3:
                road_dir = 0
            elif cos_sim > 0:
                road_dir = +1
            else:
                road_dir = -1

            return signed_d, road_dir

        # ✅ THIS preserves the original index perfectly
        tqdm.pandas(desc="Adding signed distances and directions")
        gdf[["signed_distance", "road_dir"]] = (
            gdf.progress_apply(signed_distance, axis=1, result_type="expand")
        )
        return gdf

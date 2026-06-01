from tqdm import tqdm
import numpy as np


def get_timebin_index(ts):
    # Hour
    hour = ts.hour

    # Day of week (Monday = 0, Sunday = 6)
    day_of_week = ts.day_of_week
    # print(day_of_week)
    # Season
    def get_season(month):
        return 0 if month == 12 else month // 3

    season = get_season(ts.month)
    idx = season*7*24 + day_of_week*24 + hour
    return idx

def heading_to_unit_vector(heading_deg):
    theta = np.deg2rad(heading_deg)
    return np.sin(theta), np.cos(theta)

def add_signed_distance(gdf):
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
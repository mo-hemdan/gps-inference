import pandas as pd
from tqdm import tqdm
from .sources import GPS_TRAJECTORY_SOURCE

class RoadTypeEstimator:
    def __init__(self):
        self.source = GPS_TRAJECTORY_SOURCE
        pass    

    def estimate(self, points_per_road):
        """
        Estimates road type using a group-wise apply function.

        :param points_per_road: GeoDataFrame with GPS points matched to roads
                                Must have 'matched_road_id', 'speed' columns
        :return: DataFrame with 'road_type' and 'road_type_conf' per road
        """
        def estimate_one_road(group):
            avg_speed = group.mean()
            
            # Simple heuristic thresholds
            if avg_speed >= 80:
                road_type = "highway"
                road_i = 3
                conf = min(1.0, avg_speed / 120)
            elif avg_speed >= 40:
                road_type = "city"
                road_i = 2
                conf = min(1.0, avg_speed / 80)
            else:
                road_type = "residential"
                road_i = 1
                conf = min(1.0, avg_speed / 40)
            
            return road_i, conf, self.source

        # Apply function to each road group
        tqdm.pandas(desc="Estimating road types")
        road_types_df = points_per_road['speed'].progress_apply(estimate_one_road).apply(pd.Series)
        road_types_df.columns = ["road_type", "road_type_conf", "road_type_source"]

        return road_types_df
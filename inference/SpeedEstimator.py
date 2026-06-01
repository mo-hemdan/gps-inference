import numpy as np
from .sources import OSM_SOURCE, GPS_TRAJECTORY_SOURCE

def snap_to_5(x):
    return 5 * np.round(x / 5)

class SpeedEstimator:
    def __init__(self):
        '''
        Extractor for speed estimation from GPS data
        Assumes that the GPS points have been map-matched to roads
        The function estimates the average speed per road segment and also the minimum and maximum speeds
         observed on each road segment.
         The algorithm uses simple statistical aggregation (mean, min, max) on the speeds of the GPS points
         that have been matched to each road segment.
        Values are snapped to the nearest multiple of 5 for better interpretability.
        :param self: Description
        '''
        self.confidence = 0.7  # TODO: Please change this when the data is available and not to be hard coded like this
        self.source = GPS_TRAJECTORY_SOURCE
    

    # Getting the average speed per temporal category
    def estimate(self, points_per_timezone, points_per_road):

        avg_speed_per_timezone = points_per_timezone['speed'].mean().to_frame("avg_speed")
        avg_speed_per_timezone['avg_speed_conf'] = self.confidence
        avg_speed_per_timezone['avg_speed_source'] = self.source

        speed_limits = points_per_road['speed'].agg(['min', 'max'])
        speed_limits['min'] = snap_to_5(speed_limits['min'])
        speed_limits['max'] = snap_to_5(speed_limits['max'])
        speed_limits.rename(columns={'min': 'min_speed', 'max': 'max_speed'}, inplace=True)
        speed_limits['min_speed_conf'] = self.confidence
        speed_limits['max_speed_conf'] = self.confidence
        speed_limits['min_speed_source'] = self.source
        speed_limits['max_speed_source'] = self.source
        return avg_speed_per_timezone, speed_limits
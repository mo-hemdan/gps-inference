import pandas as pd
from .sources import GPS_TRAJECTORY_SOURCE

class OnewayEstimator:
    def __init__(self):
        '''
        Estimates whether a road is oneway or not based on GPS points
         associated with the road segment.

        simply if there is a single direction of travel among the points matched to the road segment,
         the road is classified as oneway. Otherwise, it is classified as bidirectional.
         

        Currently the algorithm is quite simple and can be improved in the future
        The algorithm uses the heading of GPS points to determine the direction of travel.
        If the majority of points have headings in one direction, the road is classified as oneway.
        Otherwise, it is classified as bidirectional.
        :param self: Description
        '''
        self.confidence = 0.7   #TODO: Please change this when the data is available and not to be hard coded like this
        self.source = GPS_TRAJECTORY_SOURCE
        pass
    
    def estimate(self, points_per_road):

        def estimate_oneway(directions):
            unique_directions = directions.unique()
            oneway = len(unique_directions) == 1

            return oneway, self.confidence, self.source

        oneway_df = (
            points_per_road["road_dir"]
            .apply(estimate_oneway)
            .apply(pd.Series)
        )
        oneway_df.columns = ["oneway", "oneway_conf", "oneway_source"]
        return oneway_df
import pandas as pd
import numpy as np
from sklearn.mixture import GaussianMixture
from tqdm import tqdm 
tqdm.pandas()
from .sources import GPS_TRAJECTORY_SOURCE

class LanesAndWidthEstimator():
    def __init__(self):
        '''
        Predicts the number of lanes for a street given the points that match to this street segment
         and their signed distances from the road centerline.
        Signed distances are used to capture the spread of points across the road width.
        They have to be pre-computed during map-matching.
        The algorithm is based on Gaussian Mixture Models (GMM) for estimating the number of lanes in a specific road
        For width estimation, we use percentiles of the signed distances.
        :param self: Description
        '''
        self.criterion = "bic"
        self.max_components = 4
        self.random_state = 0
        self.width_percentile = 95
        self.width_conf = 0.7
        self.nlanes_conf_reduction = 0.2
        self.source = GPS_TRAJECTORY_SOURCE

    def estimate(self, points_per_road):
        tqdm.pandas(desc="Computing Gaussian Mixture Models for Lanes and Width")

        lanes_and_width = points_per_road['signed_distance']\
                                .progress_apply(self.estimate_num_components)\
                                .apply(pd.Series)
        lanes_and_width.columns = ["nlanes", "nlanes_conf", "nlanes_source", "width", 'width_conf', 'width_source']
        return lanes_and_width
    
    def estimate_num_components(self, distances):
        # distances: 1D array-like
        if len(distances) < self.max_components:
            return None, None
        
        X = np.asarray(distances).reshape(-1, 1)  # GMM expects 2D (n_samples, n_features)

        ks = range(1, self.max_components + 1)
        scores = []
        
        for k in ks:
            gmm = GaussianMixture(
                n_components=k,
                covariance_type="full",
                random_state=self.random_state
            )
            gmm.fit(X)
            
            if self.criterion == "bic":
                score = gmm.bic(X)
            elif self.criterion == "aic":
                score = gmm.aic(X)
            else:
                raise ValueError("criterion must be 'bic' or 'aic'")
            
            scores.append(score)
        
        best_index = int(np.argmin(scores))
        best_k = ks[best_index]
        scores_arr = np.asarray(scores, dtype=float)
        shifted_scores = -scores_arr
        exp_scores = np.exp(shifted_scores - np.max(shifted_scores))
        softmax_probs = exp_scores / exp_scores.sum()
        score = softmax_probs[best_index]


        p5 = np.percentile(distances, 100-self.width_percentile)
        p95 = np.percentile(distances, self.width_percentile)

        width = p95-p5

        return best_k, score-self.nlanes_conf_reduction, self.source, width, self.width_conf, self.source
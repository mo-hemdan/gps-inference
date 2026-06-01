import pandas as pd
import numpy as np
from collections import Counter
from scipy.stats import t

def compute_oneway(x):
   set_x = set(x)
   if set_x == {np.NaN}:
      return None
   elif '-' in set_x and '+' in set_x:
      return False
   else:
      return True
   
def compute_street_count(x):
   set_x = set(x)
   return len(set_x)
   
def calc_confidence_interval(data, alpha=0.05):

    k = len(data)
    df = k - 1

    confidence_level = 1 - alpha

    X_bar = np.mean(data)
    s = np.std(data, ddof=1)  # TODO: check ddof


    t_score = t.ppf((1 + confidence_level) / 2, df)

    standard_error = s / np.sqrt(k)
    margin_of_error = t_score * standard_error

    lower_bound = round(X_bar - margin_of_error, 2)
    upper_bound = round(X_bar + margin_of_error, 2)

    c_i = (lower_bound, upper_bound)
    
    return c_i, X_bar

def get_functional_row(s, avg_speed, travel_time, max_speed, min_speed):
   # get flow
   fl = Counter(s['Compass_dir'])
   key_to_delete = np.NaN
   try:
      del fl[key_to_delete]
   except:
      pass

   # get box plot for speed
   # Convert to pandas Series
   data_series = pd.Series(s[avg_speed].dropna())

   # Calculate summary statistics
   if data_series.empty or len(data_series) < 4:  # at least 4 data points needed to calculate quartiles:
      summary_stats = {'points': list(s[avg_speed].dropna())}
   else:
      summary_stats = {
         'whislo': data_series.min(),
         'q1': data_series.quantile(0.25),
         'med': data_series.median(),
         'q3': data_series.quantile(0.75),
         'whishi': data_series.max(),
         'fliers': list(data_series[(data_series < data_series.quantile(0.25) - 1.5 * (data_series.quantile(0.75) - data_series.quantile(0.25))) | 
                                 (data_series > data_series.quantile(0.75) + 1.5 * (data_series.quantile(0.75) - data_series.quantile(0.25)))])
      }
   
   # get box plot for time
   # Convert to pandas Series
   data_series = pd.Series(s[travel_time].dropna())
   # print(data_series)
   # Calculate summary statistics
   if data_series.empty or len(data_series) < 4:  # at least 4 data points needed to calculate quartiles:
      summary_stats_t = {'points': list(s[travel_time].dropna())}
   else:
      summary_stats_t = {
         'whislo': data_series.min(),
         'q1': data_series.quantile(0.25),
         'med': data_series.median(),
         'q3': data_series.quantile(0.75),
         'whishi': data_series.max(),
         'fliers': list(data_series[(data_series < data_series.quantile(0.25) - 1.5 * (data_series.quantile(0.75) - data_series.quantile(0.25))) | 
                                 (data_series > data_series.quantile(0.75) + 1.5 * (data_series.quantile(0.75) - data_series.quantile(0.25)))])
      }

   # get average speed vales
   a_s_col = s[avg_speed]
   a_s_no_nan = a_s_col.dropna()
   if len(a_s_no_nan) == 0:
      avg_ci = np.NAN
      avg_s = np.NAN
   elif len(a_s_no_nan) == 1:
      avg_ci = np.NAN
      avg_s = int(round(a_s_no_nan.item()))
   else:
      avg_ci, avg_s = calc_confidence_interval(a_s_no_nan)
      avg_s = int(round(avg_s))

   # get travel time values
   tt_col = s[travel_time]
   tt_no_nan = tt_col.dropna()
   if len(tt_no_nan) == 0:
      travel_t_ci = np.NAN
      travel_t = np.NAN
   elif len(tt_no_nan) == 1:
      travel_t_ci = np.NAN
      travel_t = round(tt_no_nan.item(), 4)
   else:
      travel_t_ci, travel_t = calc_confidence_interval(tt_no_nan)
      round(travel_t, 4)

   # get max speed values
   max_no_nan = s[max_speed].dropna()
   min_no_nan = s[min_speed].dropna()
   if len(max_no_nan) == 0:
      max_s = np.NAN
   elif len(max_no_nan) == 1:
      max_s = max_no_nan.item()
   else:
      max_s = int(round(max(max_no_nan)))
    
   # get min speed values
   min_no_nan = s[min_speed].dropna()
   if len(min_no_nan) == 0:
      min_s = np.NAN
   elif len(min_no_nan) == 1:
      min_s = min_no_nan.item()
   else:
      min_s = int(round(min(min_no_nan)))

   return avg_s, avg_ci, max_s, min_s, travel_t, travel_t_ci, dict(fl), summary_stats, summary_stats_t

def get_functional_metadata(df, val, time_bin, avg_speed, avg_speed_ci, max_speed, min_speed, travel_time, travel_time_ci, flow, traj_count):

   # define columns
   cols = [val, time_bin, avg_speed, avg_speed_ci, max_speed, min_speed, travel_time, travel_time_ci, flow, 'Boxplot_speed', 'Boxplot_time', traj_count]
   # list to append new rows
   rows = []
   # define time bins (for functional vals)
   unique_time_bins = [-1, 1, 0, 2]
   # get unique values
   unique_vals = np.unique(df[val].dropna())

   # for every unique val (edge/node)
   for v in unique_vals:
      # create subset df
      v_df = df[df[val] == v]
      # check size of df
      if len(v_df) < 7:
         # compute all trajectories together regardless of time bin
         avg_s, avg_ci, max_s, min_s, travel_t, travel_t_ci, fl, boxplot_stats, boxplot_stats_t = get_functional_row(v_df, avg_speed, travel_time, max_speed, min_speed)
         new_row = [v, 3, avg_s, avg_ci, max_s, min_s, travel_t, travel_t_ci, fl, boxplot_stats, boxplot_stats_t, len(v_df)]
         rows.append(new_row)
      else:
         # make a row for each time bin
         for b in unique_time_bins:
            # create subset df
            b_df = v_df[v_df[time_bin] == b]
            avg_s, avg_ci, max_s, min_s, travel_t, travel_t_ci, fl, boxplot_stats, boxplot_stats_t = get_functional_row(b_df, avg_speed, travel_time, max_speed, min_speed)
            new_row = [v, b, avg_s, avg_ci, max_s, min_s, travel_t, travel_t_ci, fl, boxplot_stats, boxplot_stats_t, len(b_df)]
            rows.append(new_row)

   functional_df = pd.DataFrame(rows, columns=cols)
   return functional_df

def get_edge_metadata(df, val, time_bin, avg_speed, avg_speed_ci, max_speed, min_speed, travel_time, travel_time_ci, flow, traj_count, osm_e_df):
   '''
   Using the saved osm information as well as the trajectory segment information, 
   return the edge structural and functional data:
      structural - Edge,Vector,     Oneway,Trajectory_count,      OSM_oneway,OSM_lanes,OSM_name,OSM_highway,OSM_maxspeed,OSM_length,
      functional - Edge, speed, speed CI, box_plots info, travel_time, CIs, trajectory_count
   '''
   ### Compute functional metadata
   e_f_df = get_functional_metadata(df, val, time_bin, avg_speed, avg_speed_ci, max_speed, min_speed, travel_time, travel_time_ci, flow, traj_count)

   ### Compute structural metadata
   # compute oneway and total num of trajectories columns
   oneway_col = df.groupby(val).agg({'Compass_dir': [compute_oneway]})
   num_traj_col = e_f_df.groupby(val).agg({traj_count: ['sum']})
   
   def grab_s_data(x):
      oneway = oneway_col.xs(x).item()
      t_count = num_traj_col.xs(x).item()

      return oneway, t_count
   
   osm_e_df[['Oneway', traj_count]] = osm_e_df[val].apply(lambda x: pd.Series(grab_s_data(x)))
   
   return osm_e_df, e_f_df

def get_node_metadata(df, val, time_bin, avg_speed, avg_speed_ci, max_speed, min_speed, travel_time, travel_time_ci, flow, traj_count, osm_n_df):
   ### Compute functional metadata
   n_f_df = get_functional_metadata(df, val, time_bin, avg_speed, avg_speed_ci, max_speed, min_speed, travel_time, travel_time_ci, flow, traj_count)

   ### Compute structural metadata
   # compute street count and total num of trajectories columns
   street_count_col = df.groupby(val).agg({'Compass_dir': [compute_street_count]})
   num_traj_col = n_f_df.groupby(val).agg({traj_count: ['sum']})

   def grab_s_data(x):
      try:
         st_count = street_count_col.xs(x).item()
         t_count = num_traj_col.xs(x).item()
      except Exception as e:
         st_count = 0
         t_count = 0
         print('Exception: x: ', x) #TODO: figure out why there's one nan value being passed
      return st_count, t_count

   osm_n_df[val].dropna()
   osm_n_df[['Street_count', traj_count]] = osm_n_df[val].apply(lambda x: pd.Series(grab_s_data(x)))

   return osm_n_df, n_f_df
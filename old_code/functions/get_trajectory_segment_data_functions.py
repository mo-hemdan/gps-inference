import pandas as pd
import numpy as np
from collections import Counter
import ast
from .utils import time_difference, distance_difference

########################################## HELPER FUNCTIONS ##########################################
def get_vector(x1, y1, x2, y2):
    # Calculate the vector components
    vector_x = x2 - x1
    vector_y = y2 - y1

    vector = [vector_x, vector_y]
    return vector

def get_trip_segment_metadata(df, trip_id, node, edge, avg_speed, max_speed, min_speed, compass_dir, day_type, time_type, travel_time, edge_vector_df, time_bin, speed, timestamp, latitude, longitude):

    # get unique trip_ids
    unique_trip_ids = np.unique(df[trip_id])

    # define df cols
    e_cols = [trip_id, edge, avg_speed, max_speed, min_speed, compass_dir, day_type, time_type, travel_time]
    n_cols = [trip_id, node, avg_speed, max_speed, min_speed, compass_dir, day_type, time_type, travel_time]

    # get edge and node df
    edge_df = get_e_n_df(df, unique_trip_ids=unique_trip_ids, cols=e_cols, val = edge, trip_id=trip_id, node=node, edge_vector_df=edge_vector_df, time_bin=time_bin, day_type=day_type, time_type=time_type, speed=speed, timestamp=timestamp, latitude=latitude, longitude=longitude)
    node_df = get_e_n_df(df, unique_trip_ids=unique_trip_ids, cols=n_cols, val = node, trip_id=trip_id, node=node, edge_vector_df=edge_vector_df, time_bin=time_bin, day_type=day_type, time_type=time_type, speed=speed, timestamp=timestamp, latitude=latitude, longitude=longitude)

    return edge_df, node_df

def get_e_n_df(df, unique_trip_ids, cols, val, trip_id, node, edge_vector_df, time_bin, day_type, time_type, speed, timestamp, latitude, longitude):

    # create row list to append values
    rows = []

    # for every unique trip id
    for trip in unique_trip_ids:

        # create subset df
        t_df = df[df[trip_id] == trip]

        # get unique edges/nodes
        unique_e_n = np.unique(t_df[val].dropna())
        # print(f't_df: {t_df.head(3)}')
        # print(f'length of d_df: {len(t_df)}')
        # for every unique edge/node
        for v in unique_e_n:
            # print(f'current v: {v}')

            if val == node:
                v_vector = None
            else:
                v_vector = edge_vector_df[edge_vector_df['Edge'] == v]['Vector'].item()

            v_df = t_df[t_df[val] == v]     # create subset df

            avg_speed, max_speed, min_speed, c_dir, d_type, t_type, travel_t = get_e_n_segment_metadata(v_df, v_vector, speed, day_type, time_type, timestamp, latitude, longitude)     # get metadata

            if val == node:
                v = int(v)
            else:
                v = ast.literal_eval(v)

            new_row = trip, v, avg_speed, max_speed, min_speed, c_dir, d_type, t_type, travel_t
            rows.append(new_row)

    new_df = pd.DataFrame(rows, columns=cols)

    # calculate time_bin col
    new_df[time_bin] = new_df[day_type] + new_df[time_type]

    return new_df

def get_travel_time(df, timestamp, longitude, latitude, h_d=False):
    ''' 
    Returns travel time in minutes
    h_d (bool) - False if you just want the time difference between the first and last point,
                 True if you want the time difference divided by the length of the intersection/road
    '''
    # get first and last points of that trajectory segment
    first_point = df.loc[df[timestamp] == min(df[timestamp])]
    last_point = df.loc[df[timestamp] == max(df[timestamp])]

    f_lat = list(first_point[latitude])[0]
    f_long = list(first_point[longitude])[0]
    f_timestamp = list(first_point[timestamp])[0]

    l_lat = list(last_point[latitude])[0]
    l_long = list(last_point[longitude])[0]
    l_timestamp = list(last_point[timestamp])[0]

    # get the time difference between the first and last point
    time_dif = time_difference(p_1=f_timestamp, p_2=l_timestamp, units='minutes')

    if h_d:
        # get the distance between the first and last point
        distance = distance_difference(lat_1=f_lat, lat_2=l_lat, long_1=f_long, long_2=l_long)
        # compute travel time
        tt = np.divide(time_dif, distance)   # if want minutes/miles
        travel_time = round(tt, 4)
    else:
        # compute travel time
        travel_time = round(time_dif, 4)
    
    return travel_time

def get_e_n_segment_metadata(df, v_vector, speed, day_type, time_type, timestamp, latitude, longitude):
    if len(df) == 1:
        one_speed = int(round(df[speed].item()))
        d_type = df[day_type].item()
        t_type = df[time_type].item()
        return one_speed, one_speed, one_speed, np.NaN, d_type, t_type, np.NaN
    
    else:
        ### get speed statistics
        # check if nan value:
        try:
            avg_speed = int(round(np.mean(df[speed])))
            max_speed = int(round(max(df[speed])))
            min_speed = int(round(min(df[speed])))
        except Exception as e:
            avg_speed, max_speed, min_speed = np.NaN, np.NaN, np.NaN
            print(e)

        ### get compass directions (vector or edge name)

        # get first and last points of that trajectory segment
        first_point = df.loc[df[timestamp] == min(df[timestamp])]
        last_point = df.loc[df[timestamp] == max(df[timestamp])]
        if v_vector == None:
            # node case:
            c_dir = last_point['Edge'].item()
            
        else:
            # edge case:
            # get location of first and last points
            f_lat = list(first_point[latitude])[0]
            f_long = list(first_point[longitude])[0]
            l_lat = list(last_point[latitude])[0]
            l_long = list(last_point[longitude])[0]

            # get vector of trajectory segment
            segment_vector = get_vector(f_long, f_lat, l_long, l_lat)

            # compute dot product
            dot_product = np.vdot(ast.literal_eval(v_vector), segment_vector)

            if dot_product > 0:
                c_dir = '+'
            elif dot_product < 0:
                c_dir = '-'
            else:
                c_dir = 'p'

        ### day type
        d_type = get_most_frequent_value(df[day_type])
        ### time type
        t_type = get_most_frequent_value(df[time_type])

        ### travel time
        travel_t = get_travel_time(df, timestamp, longitude, latitude)
    
    return avg_speed, max_speed, min_speed, c_dir, d_type, t_type, travel_t


def get_most_frequent_value(col):
    
    counter = Counter(col)
    categories = list(counter.keys())
    counts = list(counter.values())

    max_idx = counts.index(max(counts))

    most_frequent_val = categories[max_idx]

    return most_frequent_val


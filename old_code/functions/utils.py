import datetime
import numpy as np
from geopy.distance import geodesic as GD
import json

def return_datetime_type(p):
   ''' 
   Returns point as datetime.datetime object
   '''
   if not isinstance(p, datetime.datetime) and not isinstance(p, str):
      raise TypeError('Input is not of type datetime.datetime or str')
   else:
      if type(p) == datetime.datetime:
         return p
      else:
         new_p = datetime.datetime.strptime(p, '%Y-%m-%d %H:%M:%S+03')
         return new_p

def time_difference(p_1, p_2, units='hours'): 
    ''' 
    IN: p_1, p_2 (datetime.datetime OR str) - timestamp of two points in  year-month-day hour-minute-seconds

    OUT: time difference (float OR None) - time difference between timestamps in hours if points of correct type, else None
    '''
    # make points be of datetime type
    dt_p1 = return_datetime_type(p_1)
    dt_p2 = return_datetime_type(p_2)

    # check points are correct type
    if type(dt_p1) == None or type(dt_p2) == None:
        return np.NAN
    # if they are, get time difference between them
    else:
        # get timedelta
        dif = dt_p2 - dt_p1

        d = dif.days
        s = dif.seconds
        ms = dif.microseconds

        if units == 'hours':
            hours = np.multiply(d, 24) + np.divide(s, 3600) + np.divide(ms, 3600000)
            return hours
        
        elif units == 'minutes':
            minutes = np.multiply(d, 1440) + np.divide(s, 60) + np.divide(ms, 60000)
            return minutes

        else: 
            raise ValueError('Units is not one of the following units: ("hours", "minutes").')

def distance_difference(lat_1, lat_2, long_1, long_2):
   '''
   IN: lat_1, lat_2, long_1, long_2 (float) - latitude and longitude coordinates for two points: (lat_1, long_1), (lat_2, long_2) 

   OUT: dif (float) - geodesic distance in miles between two points
   '''
   # create point tuples
   p_1 = (lat_1, long_1)
   p_2 = (lat_2, long_2)

   # use geodesic function from geopy to calculate distance
   dif = GD(p_1, p_2).miles

   return dif

def load_constants(object, constants_dict):
    
    # get dir paths
    object.INPUT_DIR = constants_dict['input directory']
    object.PROCESS_DIR = constants_dict['processed directory']
    object.OUT_DIR = constants_dict['output directory']

    object.INPUT_FILENAME = constants_dict['input file name']
    object.TRAJ_METADATA_OUT_FILENAME = constants_dict['trajectory metadata out']

    # check if speed and heading need to be calculated
    object.SPEED_BOOL = constants_dict['trajectory cols']['speed bool']
    object.HEADING_BOOL = constants_dict['trajectory cols']['heading bool']
    object.TIMESTAMP_COLNAME= constants_dict['trajectory cols']['timestamp col name']
    object.SPEED_COLNAME = constants_dict['trajectory cols']['speed col name']
    object.HEADING_COLNAME = constants_dict['trajectory cols']['heading col name']
    object.LAT_COLNAME = constants_dict['trajectory cols']['latitude col name']
    object.LON_COLNAME = constants_dict['trajectory cols']['longitude col name']
    object.TRIP_ID = constants_dict['trajectory cols']['trip id']

    # get metadata column names
    object.CAMPASS_COLNAME = constants_dict['metadata cols']['compass directions']
    object.DAY_COLNAME = constants_dict['metadata cols']['day']
    object.DAY_TYPE_COLNAME = constants_dict['metadata cols']['day type']
    object.TIME_TYPE_COLNAME = constants_dict['metadata cols']['time type']
    object.TIME_BIN_COLNAME = constants_dict['metadata cols']['time bin']
    object.AVGSPEED_COLNAME = constants_dict['metadata cols']['avg speed']
    object.MAXSPEED_COLNAME = constants_dict['metadata cols']['max speed']
    object.MINSPEED_COLNAME = constants_dict['metadata cols']['min speed']
    object.TRAVEL_TIME_COLNAME = constants_dict['metadata cols']['travel time']
    object.DIRECTION_COLNAME= constants_dict['metadata cols']['directions']
    object.FLOW_COLNAME = constants_dict['metadata cols']['flow']
    object.AVGSPEED_CI_COLNAME = constants_dict['metadata cols']['avg speed CI']
    object.TRAVEL_TIME_CI_COLNAME = constants_dict['metadata cols']['travel time CI']
    object.TRAJ_COUNT_COLNAME = constants_dict['metadata cols']['count']

    object.OSM_EDGE_COLNAMES = constants_dict['metadata cols']['OSM edge col names']
    object.OSM_EDGE_NEW_COLNAMES = constants_dict['metadata cols']['OSM edge new col names']
    object.OSM_NODE_COLNAMES = constants_dict['metadata cols']['OSM node col names']
    object.OSM_NODE_NEW_COLNAMES = constants_dict['metadata cols']['OSM node new col names']

    # get metadata column names
    object.EDGE_COLNAME = constants_dict['metadata cols']['edge']
    object.NODE_COLNAME = constants_dict['metadata cols']['node']

    # OSM Related Information
    object.OSM_NODE_INFOFILE = constants_dict['OSM node info file']
    object.OSM_EDGE_INFOFILE = constants_dict['OSM edge info file']

    # get map matching values
    object.NETWORK_TYPE = constants_dict['map matching vals']['network type']
    object.MAPMATCHING_OUT_FILENAME = constants_dict['map matching out']

    object.EDGE_DF_NAME = constants_dict['trajectory segment out']['edge df']
    object.NODE_DF_NAME = constants_dict['trajectory segment out']['node df']


    # out
    object.NODE_STATIC_METADATA_OUT_FILENAME= constants_dict['map metadata out']['node structural']
    object.NODE_FUNCTIONAL_METADATA_OUT_FILENAME = constants_dict['map metadata out']['node functional']
    object.EDGE_STATIC_METADATA_OUT_FILENAME = constants_dict['map metadata out']['edge structural']
    object.EDGE_FUNCTIONAL_METADATA_OUT_FILENAME = constants_dict['map metadata out']['edge functional']
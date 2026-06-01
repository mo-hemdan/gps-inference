import numpy as np
from .utils import *

########################################## HELPER FUNCTIONS ########################################## 
def mph(r_1, r_2, cols=['Position Date Time', 'lat', 'long']):
    
   # get values
   t_1 = r_1[cols[0]]
   t_2 = r_2[cols[0]]
   
   lat_1 = r_1[cols[1]]
   lat_2 = r_2[cols[1]]

   long_1 = r_1[cols[2]]
   long_2 = r_2[cols[2]]

   # get time difference (hours)
   t_dif = time_difference(t_1, t_2)

   # get distance difference (miles)
   d_dif = distance_difference(lat_1=lat_1, lat_2=lat_2, long_1=long_1, long_2=long_2)

   # compute miles per hour
   dx_dt = np.divide(d_dif, t_dif)

   return dx_dt

# get all cardinal directions for the unique headings (binning headings into N,S,E,W,NE,NW, etc)
def get_compass_dir(x):
   if 337.5 <= x <= 360 or 0 <= x < 22.5:
      return 'N'
   elif 22.5 <= x < 67.5:
      return 'NE'
   elif 67.5 <= x < 112.5:
      return 'E'
   elif 112.5 <= x < 157.5:
      return 'SE'
   elif 157.5 <= x < 202.5:
      return 'S'
   elif 202.5 <= x < 247.5:
      return 'SW'
   elif 247.5 <= x < 292.5:
      return 'W'
   elif 292.5 <= x < 337.5:
      return 'NW'
   else:
      raise ValueError('Bearing not within bearing values (0-360).')
    
def get_day_type(t):

   dt_t = return_datetime_type(t)  # turn t into a datetime object
   weekday = dt_t.isoweekday()    # get weekday (0 - Monday, 6 - Sunday)

   if 1 <= weekday <= 5:
      return 1
   elif 6 <= weekday <= 7:
      return 0
   else:
      raise ValueError('Weekday value not within the datetime.isoweekday values (1-7).')
    
def get_day(t):

   dt_t = return_datetime_type(t)  # turn t into a datetime object
   weekday = dt_t.isoweekday()    # get weekday (0 - Monday, 6 - Sunday)
   
   if 1 <= weekday <= 7:
      return weekday
   
   ### Returns strings instead of int if needed
   # if weekday == 0:
   #     return 'M'
   # elif weekday == 1:
   #     return 'T'
   # elif weekday == 2:
   #     return 'W'
   # elif weekday == 3:
   #     return 'R'
   # elif weekday == 4:
   #     return 'F'
   # elif weekday == 5:
   #     return 'Sa'
   # elif weekday == 6:
   #     return 'Su'
   else:
      raise ValueError('Weekday value not within the datetime.isoweekday values (1-7).')
   
def get_time_type(t):
   dt_t = return_datetime_type(t)
   hour = dt_t.hour

   if 0 <= hour < 4:
      return -1
   elif 4 <= hour <= 18:
      return 1
   elif 18 < hour <= 23:
      return -1
   else:
      raise ValueError('Hour value not within regular hour times (0 - 23)')
   
def get_time_bin(d, t):
   if not isinstance(d, int) and not isinstance(t, int):
      raise TypeError('Day or time type is not an int.')
   else:
      bin = d + t
      return bin

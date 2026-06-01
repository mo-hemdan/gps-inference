import psycopg2
import numpy as np
colname_idx = None
## ['id', 'dataset', 'traj_id', 'order_id', 'timestamp', 'speed', 'angle', 'accuracy', 'processed', 'matched_road_osm_id', 'geometry', 'driving_mode', 'osname']
def get_timebin(dt):
    # Hour
    hour = dt.hour

    # Day of week (Monday = 0, Sunday = 6)
    day_of_week = dt.weekday()

    # Season
    def get_season(month):
        if month in (12, 1, 2):
            return 0
        elif month in (3, 4, 5):
            return 1
        elif month in (6, 7, 8):
            return 2
        else:
            return 3

    season = get_season(dt.month)
    return season, day_of_week, hour

def initialize_state():
    return {
        'v_min': float('inf'),
        'v_max': float('-inf'),
        'd_left': float('-inf'),
        'd_right': float('-inf'),
        'mu_d': 0,
        'n_d': 0,
        'M_d': 0,
        'n_forward': 0,
        'n_backward': 0,
        'v': dict()
    }

def initialize_temporal_state():
    return {
        'n': 0,
        'mu': 0,
        'M': 0
    }

def angle_to_unit_vector(angle_deg):
    angle_rad = np.deg2rad(angle_deg)
    return np.cos(angle_rad), np.sin(angle_rad)
def dot_from_angles(angle1, angle2):
    v1 = angle_to_unit_vector(angle1)
    v2 = angle_to_unit_vector(angle2)
    return v1[0]*v2[0] + v1[1]*v2[1]

def process_batch(rows):
    # Your processing logic here
    print(f"Processing batch of size: {len(rows)}")
    # Example: iterate rows
    road_metadata = dict()
    for row in rows:
        r = row[colname_idx['matched_road_osm_id']]
        if r not in road_metadata: road_metadata[r] = dict()
        season, day_of_week, hour = get_timebin(row[colname_idx['timestamp']])
        timebin = season*7*24 + day_of_week*24 + hour

        road_metadata[r]['v_min'] = min([road_metadata[r]['v_min'], row[colname_idx['speed']]])
        road_metadata[r]['v_max'] = max([road_metadata[r]['v_max'], row[colname_idx['speed']]])

        road_metadata[r]['d_left'] = max([road_metadata[r]['d_left'], row[colname_idx['signed_d']]])
        road_metadata[r]['d_right'] = max([road_metadata[r]['d_right'], row[colname_idx['signed_d']]])

        road_metadata[r]['n_d'] += 1

        delta = row[colname_idx['signed_d']] - road_metadata[r]['mu_d']
        road_metadata[r]['mu_d'] += delta/road_metadata[r]['n_d']

        delta2 = row[colname_idx['signed_d']] - road_metadata[r]['mu_d']
        road_metadata[r]['M_d'] += delta*delta2

        res = dot_from_angles(row[colname_idx['angle']], row[colname_idx['r_angle']])
        if res >= 0: road_metadata[r]['n_forward'] += 1
        else:        road_metadata[r]['n_backward'] += 1

        if timebin not in road_metadata[r]['v']: road_metadata[r]['v'][timebin] = initialize_temporal_state()
        road_metadata[r]['v'][timebin]['n'] += 1




20: 𝛿 ←𝑝.𝑠𝑝𝑒𝑒𝑑−𝐷[𝑟].𝑣[𝑡].𝜇
21: 𝐷[𝑟].𝑣[𝑡].𝜇 ←𝐷[𝑟].𝑣[𝑡].𝜇+ 𝛿
𝐷[𝑟].𝑣[𝑡].𝑛
22: 𝛿2 ←𝑝.𝑠𝑖𝑔𝑛𝑒𝑑_
𝑑−𝐷[𝑟].𝜇𝑑
23: 𝐷[𝑟].𝑣[𝑡].𝑀 ←𝐷[𝑟].𝑣[𝑡].𝑀+𝛿∗𝛿2


        print(row)
        break


conn = psycopg2.connect(
    dbname="gis",
    user="gis",
    password="gis",
    host="localhost",
    port=5432
)

# Server-side cursor (important!)
cursor = conn.cursor(name="batch_cursor")

cursor.execute("SELECT * FROM gps_points;")

colnames = [desc[0] for desc in cursor.description]
colname_idx = {col: i for i, col in enumerate(colnames)}

BATCH_SIZE = 10000

while True:
    rows = cursor.fetchmany(BATCH_SIZE)
    if not rows:
        break
    

    process_batch(rows)
    break

cursor.close()
conn.close()
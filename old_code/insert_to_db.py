# %%
import pandas as pd

df = pd.read_csv('data/edge_s.csv')


# %%
df.head()
# %%
df.drop(columns = ['OSM_length', 'OSM_lanes', 'OSM_name', 'OSM_highway', 'OSM_maxspeed'], inplace=True)

# %%
# df[df['osmid'].apply(lambda x: '[' in x)]
df.head()
# %%
def resolve_oneway(group):
    if False in group.values:
        return False
    elif True in group.values:
        return True
    else:
        return False
# Group by 'osmid' and apply logic to 'oneway'
result = df.groupby('osmid')['Oneway'].apply(resolve_oneway).reset_index()

# %%
result.rename(columns={'osmid': 'id', 'Oneway': 'inf_oneway_direction'}, inplace=True)

# %%
result.head()

#%%
result.shape

# %%

import psycopg2
from psycopg2.extras import execute_values

# Connect to DB
conn = psycopg2.connect(
    dbname="gis",
    user="gis",
    password="gis",
    host="cs-u-spatial-406.cs.umn.edu",  # or wherever your DB is hosted
    port=5432
)
cur = conn.cursor()

# Prepare data as list of tuples
data = list(result.itertuples(index=False, name=None))

# Perform UPSERT
query = """
UPDATE roads
SET inf_oneway_direction = data.inf_oneway_direction
FROM (VALUES %s) AS data(id, inf_oneway_direction)
WHERE roads.id = data.id;
"""

# Efficient batch insert
execute_values(cur, query, data)

conn.commit()
cur.close()
conn.close()
# %%
def resolve_oneway_osm(group):
    if False in group.values:
        return False
    elif True in group.values:
        return True
    else:
        return None

agg_result = df.groupby('osmid').agg({
    'Oneway': resolve_oneway,
    'OSM_oneway': resolve_oneway_osm
}).reset_index()


# %%
agg_result

# %%
accuracy = (df['Oneway'] == df['OSM_oneway']).mean()
print(f"Accuracy: {accuracy:.4f}")
# %%

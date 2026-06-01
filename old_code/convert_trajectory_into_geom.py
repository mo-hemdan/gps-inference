# %%
import pandas as pd

data_filename = "datasets/city=Jakarta/"  # part-00000-8bbff892-97d2-4011-9961-703e38972569.c000.snappy.parquet"

df = pd.read_parquet(data_filename, engine="pyarrow")

#%%

top = -6.1701
left = 106.7709
right = 106.8340
bottom = -6.2059
minx, miny, maxx, maxy = left, bottom, right, top

subset = df[
    (df.rawlng <= maxx) &
    (df.rawlng >= minx) &
    (df.rawlat <= maxy) &
    (df.rawlat >= miny)
]

df = subset
# %%
from shapely.geometry import LineString

# Explicitly select the columns you want to operate on
traj_groupby_df = df.sort_values(by=["trj_id", "pingtimestamp"]).groupby("trj_id")

geom = traj_groupby_df[["rawlat", "rawlng"]].apply(
    lambda group: LineString(zip(group["rawlng"], group["rawlat"])).wkt
    if len(group) >= 2
    else None
)

timestamp = traj_groupby_df["pingtimestamp"].apply(list)

# %%
df = pd.DataFrame({"geom": geom, "timestamp": timestamp})
# df.drop(columns=['timestamp'], inplace=True)

# %%
df.reset_index(inplace=True)
df.rename(columns={'trj_id': 'id'}, inplace=True)
# # df.set_index("trj_id")
# #     .dropna(subset=["geometry"])
# df.index = df.trj_id
# df.reset_index()
# df.index.name = "id"
# df.reset_index()
# %%
df.to_csv("fmm/gps_data/jakarta/trj_id.csv", sep=";", index=False)

# %%
# trajectory_df = (
#     df.sort_values(by=["trj_id", "pingtimestamp"])
#     .groupby("trj_id")[["rawlat", "rawlng"]]
#     .apply(
#         lambda group: LineString(zip(group["rawlng"], group["rawlat"])).wkt
#         if len(group) >= 2
#         else None
#     )
#     .reset_index(name="geometry")
#     .dropna(subset=["geometry"])
# )

# # %%
# # trajectory_df.to_parquet("datasets/city=Jakarta_traj_geoms.parquet", index=False)

# # %%
# trajectory_df.to_csv("datasets/city=Jakarta_traj_geoms.csv", index=False)

# # %%
# from shapely.wkt import loads

# trajectory_df["geometry"] = trajectory_df["geometry"].apply(loads)

# # %%

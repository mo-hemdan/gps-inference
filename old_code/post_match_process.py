# %%
import pandas as pd


df = pd.read_csv('fmm/tmp/jakarta/mr_0.txt', sep=';')

# %%
new_df = df[~df.opath.isna()]

# %%
import geopandas as gpd
network = gpd.read_file('fmm/graphs/jakarta/edges.shp')
network.head()
# %%

full_trj = pd.read_csv('fmm/gps_data/jakarta/trips.csv', sep=';')

# %%
full_trj.head()
# %%

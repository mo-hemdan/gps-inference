# %%
import pandas as pd

BASE_DIR = '/mnt/fastssd/mapedia_datasets/roma_taxi/'

import pandas as pd
import re

# ---- input / output ----
input_file = BASE_DIR+"taxi_february.txt"        # your file
output_file = BASE_DIR+"taxi.parquet"

# ---- read raw file ----
df = pd.read_csv(
    input_file,
    sep=";",
    header=None,
    names=["trip_id", "timestamp", "point"]
)

# ---- parse POINT(lat lon) ----
def parse_point(p):
    match = re.search(r"POINT\(([^ ]+) ([^ ]+)\)", p)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

df[["lat", "lon"]] = df["point"].apply(
    lambda p: pd.Series(parse_point(p))
)

# ---- convert timestamp ----
# ---- timestamp parsing (mixed formats, timezone-aware) ----
df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    format="mixed"
)

# ---- drop raw geometry if not needed ----
df = df.drop(columns=["point"])

# ---- save to parquet ----
df.to_parquet(output_file, engine="pyarrow", index=False)

print("Saved to", output_file)

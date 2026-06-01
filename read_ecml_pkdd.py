import pandas as pd
import json
from pathlib import Path
from tqdm import tqdm

# ------------------
# Paths
# ------------------
BASE_DIR = Path("/mnt/fastssd/mapedia_datasets/ecml_pkdd/")
TRAIN_PATH = BASE_DIR / "train.csv"   # Porto taxi dataset
TEST_PATH = BASE_DIR / "test.csv"   # Porto taxi dataset
OUTPUT_PATH = BASE_DIR / "porto_taxi_points.parquet"

# ------------------
# Read dataset
# ------------------
train_df = pd.read_csv(TRAIN_PATH)
test_df = pd.read_csv(TEST_PATH)
df = pd.concat([train_df, test_df])


# Convert trip start timestamp
df["trip_start_time"] = pd.to_datetime(df["TIMESTAMP"], unit="s")

# ------------------
# Expand POLYLINE
# ------------------
rows = []

for _, row in tqdm(df.iterrows(), total=len(df), desc="Expanding trajectories"):
    if row["MISSING_DATA"]:
        continue

    try:
        polyline = json.loads(row["POLYLINE"])
    except Exception:
        continue

    for point_idx, (lon, lat) in enumerate(polyline):
        rows.append({
            "trip_id": row["TRIP_ID"],
            "taxi_id": row["TAXI_ID"],
            "call_type": row["CALL_TYPE"],
            "origin_call": row["ORIGIN_CALL"],
            "origin_stand": row["ORIGIN_STAND"],
            "daytype": row["DAY_TYPE"],

            # timing
            "trip_start_time": row["trip_start_time"],
            "point_idx": point_idx,
            "point_timestamp": row["trip_start_time"]
                                + pd.Timedelta(seconds=15 * point_idx),

            # geometry
            "lon": lon,
            "lat": lat,
        })

# ------------------
# Point-level DataFrame
# ------------------
points_df = pd.DataFrame(rows)

# Optional: enforce dtypes (saves space)
points_df = points_df.astype({
    "taxi_id": "int32",
    "point_idx": "int16",
    "lon": "float64",
    "lat": "float64",
})

print(f"Expanded to {len(points_df):,} GPS points")
print(points_df.head())

points_df["trip_id"] = points_df["trip_id"].astype(str)


# ------------------
# Save to Parquet
# ------------------
points_df.to_parquet(
    OUTPUT_PATH,
    engine="pyarrow",
    compression="snappy",
    index=False
)

print(f"Saved {len(points_df):,} GPS points → {OUTPUT_PATH}")

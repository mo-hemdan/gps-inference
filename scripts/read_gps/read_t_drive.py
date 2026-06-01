import pandas as pd
from pathlib import Path
from tqdm import tqdm

txt_dir = Path("/mnt/fastssd/mapedia_datasets/tdrive/release/taxi_log_2008_by_id")
output_parquet = "/mnt/fastssd/mapedia_datasets/tdrive/combined.parquet"

columns = ["user_id", "timestamp", "lon", "lat"]
dfs = []

for txt_file in tqdm(sorted(txt_dir.glob("*.txt")), desc="combining files"):
    df = pd.read_csv(
        txt_file,
        header=None,
        names=columns
    )
    if df.empty:
        print(f"Empty file: {txt_file}")
    dfs.append(df)

combined = pd.concat(dfs, ignore_index=True)

# 🔥 Save as Parquet
combined.to_parquet(
    output_parquet,
    engine="pyarrow",   # recommended
    compression="snappy"
)

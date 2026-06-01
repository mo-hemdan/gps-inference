import pandas as pd
from pathlib import Path
import re 


# ---- paths ----
input_dir = Path("/mnt/fastssd/mapedia_datasets/riobuses/2014-10")      # folder with txt/csv files
output_dir = Path("/mnt/fastssd/mapedia_datasets/riobuses/parquet_folder") # parquet dataset
output_dir.mkdir(parents=True, exist_ok=True)

# ---- schema ----
columns = [
    "date",
    "time",
    "bus_id",
    "bus_line",
    "latitude",
    "longitude",
    "speed"
]
# date_re = re.compile(r"^\d{2}-\d{2}-\d{4}$")
# time_re = re.compile(r"^\d{2}:\d{2}:\d{2}$")

# ---- process each file ----
for file in sorted(input_dir.glob("*.txt")):
    print(f"Processing {file.name}")

    df = pd.read_csv(
        file,
        header=None,
        names=columns,
        engine="python",
        on_bad_lines="skip"
    )

    print(f"{file.name}: read {len(df):,} valid rows")
    
    # valid_mask = (
    #     df["date"].astype(str).str.match(date_re) &
    #     df["time"].astype(str).str.match(time_re)
    # )

    # df = df[valid_mask]
    # print(f"{file.name}: kept {len(df):,} valid rows after timestamp")

    # ---- combine date + time into timestamp ----
    # Ensure strings
    df["date"] = df["date"].astype(str).str.strip()
    df["time"] = df["time"].astype(str).str.strip()

    # Keep only valid-looking dates (YYYY-MM-DD or DD-MM-YYYY)
    df = df[df["date"].str.match(r"\d{2}-\d{2}-\d{4}")]
    print(f'Kept (Data Cleaning) only {len(df)}')
    
    # Remove decimal junk like "0.0"
    df["time"] = df["time"].str.replace(r"\.0$", "", regex=True)

    # Keep only HH:MM:SS
    df = df[df["time"].str.match(r"\d{2}:\d{2}:\d{2}")]
    print(f'Kept (Time cleaning) only {len(df)}')
    
    df["timestamp"] = pd.to_datetime(
        df["date"] + " " + df["time"],
        dayfirst=True,          # important for DD-MM-YYYY
        errors="coerce"
    )
    
    df = df.dropna(subset=["timestamp"])
    print(f'Kept (Timestamp cleaning) only {len(df)}')


    # ---- cleanup ----
    df.drop(columns=["date", "time"], inplace=True)
    # df = df.dropna(subset=["latitude", "longitude"])

    df.to_parquet(
        output_dir / f"{file.stem}.parquet",
        engine="pyarrow",
        index=False,
        compression="snappy"
    )

print("All files converted successfully.")

#!/usr/bin/env python

from sodapy import Socrata
from datetime import datetime, timedelta
from tqdm import tqdm
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
import time

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
DATASET_ID = "x344-v6h6"
TIME_STEP = timedelta(days=1)
PAGE_LIMIT = 50_000
OUT_DIR = "/mnt/fastssd/mapedia_datasets/sfmta_parquet"

os.makedirs(OUT_DIR, exist_ok=True)

client = Socrata(
    "data.sfgov.org",
    app_token="5tY5K7B9FiLQOuYXqP64DmalM",
    username="71jcegtnu6fmpgobq2r4iyqzi",
    password="5x6ti4ucvchpm1vyar7omctuc5gcvorod62gh6j6lzf6rvwx1p",
    timeout=60
)

# ------------------------------------------------------------------
# METADATA
# ------------------------------------------------------------------
def get_dataset_range():
    result = client.get(
        DATASET_ID,
        select="""
            MIN(vehicle_position_date_time) AS min_time,
            MAX(vehicle_position_date_time) AS max_time
        """
    )

    min_time = datetime.fromisoformat(result[0]["min_time"])
    max_time = datetime.fromisoformat(result[0]["max_time"])

    print(f"Dataset range: {min_time} -> {max_time}")
    return min_time, max_time


# ------------------------------------------------------------------
# DOWNLOAD + WRITE ONE DAY
# ------------------------------------------------------------------
def process_one_day(day_start, day_end):
    offset = 0
    rows_written = 0

    date_str = day_start.strftime("%Y-%m-%d")
    outfile = os.path.join(OUT_DIR, f"sfmta_{date_str}.parquet")

    if os.path.exists(outfile):
        return 0, True  # already done

    writer = None

    while True:
        rows = client.get(
            DATASET_ID,
            where=f"""
                vehicle_position_date_time >= '{day_start.isoformat()}'
                AND vehicle_position_date_time < '{day_end.isoformat()}'
            """,
            limit=PAGE_LIMIT,
            offset=offset
        )

        if not rows:
            break

        df = pd.DataFrame(rows)

        # keep only relevant columns (adjust if needed)
        keep_cols = [
            "vehicle_id",
            "vehicle_position_date_time",
            "loc_x",
            "loc_y",
            "heading", # in decimal degrees from North
            "average_speed" # in mph
        ]
        df = df[[c for c in keep_cols if c in df.columns]]

        table = pa.Table.from_pandas(df, preserve_index=False)

        if writer is None:
            writer = pq.ParquetWriter(outfile, table.schema)

        writer.write_table(table)

        rows_written += len(df)

        if len(rows) < PAGE_LIMIT:
            break

        offset += PAGE_LIMIT

    if writer:
        writer.close()

    return rows_written, False


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
if __name__ == "__main__":
    start_time, end_time = get_dataset_range()

    total_days = (end_time.date() - start_time.date()).days + 1
    total_rows = 0

    pbar = tqdm(total=total_days, desc="Downloading days", unit="day")

    current = start_time.replace(hour=0, minute=0, second=0, microsecond=0)

    while current < end_time:
        next_day = current + TIME_STEP
        date_str = current.strftime("%Y-%m-%d")

        try:
            rows_today, skipped = process_one_day(current, next_day)

            if skipped:
                pbar.set_postfix(date=date_str, status="skipped")
            else:
                total_rows += rows_today
                pbar.set_postfix(
                    date=date_str,
                    rows_today=f"{rows_today:,}",
                    total_rows=f"{total_rows:,}"
                )

        except Exception as e:
            print(f"\n❌ Error on {date_str}: {e}")
            print("Retrying after sleep...")
            time.sleep(15)
            continue

        pbar.update(1)
        current = next_day
        time.sleep(0.1)

    pbar.close()

    print("\nDownload finished")
    print(f"Total rows written: {total_rows:,}")
    print(f"Parquet directory : {OUT_DIR}")

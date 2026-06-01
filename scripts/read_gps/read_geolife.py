#%%
import pandas as pd
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path("/mnt/fastssd/mapedia_datasets/geolife/Geolife Trajectories 1.3/Data")

SKIP_ROWS_HEADER_TRAJ_FILE = 6
SKIP_ROWS_HEADER_LABELS_FILE = 1

# -----------------------------
# Read one PLT file
# -----------------------------
def read_plt_to_df(plt_path: Path, user_id: int):
    traj_id = plt_path.stem

    df = pd.read_csv(
        plt_path,
        skiprows=SKIP_ROWS_HEADER_TRAJ_FILE,  # ignore header
        header=None,
        names=[
            "lat",
            "lon",
            "unused",
            "altitude_ft",
            "days_since_1899",
            "date",
            "time",
        ],
    )

    df["timestamp"] = pd.to_datetime(
        df["date"] + " " + df["time"],
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
    )

    df["user_id"] = user_id
    df["traj_id"] = traj_id

    return df


# -----------------------------
# Read labels.txt (optional)
# -----------------------------
def read_labels(labels_path: Path, user_id: int):
    """
    labels.txt format:
    Start Time      End Time        Transportation Mode
    2008/08/20 12:09:17     2008/08/20 12:45:05     walk
    """

    labels = pd.read_csv(
        labels_path,
        skiprows=SKIP_ROWS_HEADER_LABELS_FILE,                 # skip header
        sep=r"\s+",
        header=None,
        names=[
            "start_date",
            "start_time",
            "end_date",
            "end_time",
            "transportation_mode",
        ],
    )

    # Combine date + time
    labels["start_time"] = pd.to_datetime(
        labels["start_date"] + " " + labels["start_time"],
        format="%Y/%m/%d %H:%M:%S",
        errors="coerce",
    )

    labels["end_time"] = pd.to_datetime(
        labels["end_date"] + " " + labels["end_time"],
        format="%Y/%m/%d %H:%M:%S",
        errors="coerce",
    )

    labels = labels[["start_time", "end_time", "transportation_mode"]]
    labels["user_id"] = user_id

    return labels


#%%
# -----------------------------
# Main loop: user → trajectories
# -----------------------------
all_traj_dfs = []
all_label_dfs = []
total_users = len(list(BASE_DIR.iterdir()))

num_missed_labels = 0

for user_dir in tqdm(BASE_DIR.iterdir(), desc="Looping through users", total=total_users):
    if not user_dir.is_dir():
        continue

    user_id = int(user_dir.name)
    traj_dir = user_dir / "Trajectory"

    # ---- Read trajectories ----
    if traj_dir.exists():
        for plt_file in traj_dir.glob("*.plt"):
            all_traj_dfs.append(
                read_plt_to_df(plt_file, user_id)
            )

    # ---- Read labels (if exists) ----
    labels_path = user_dir / "labels.txt"
    if labels_path.exists():
        num_missed_labels += 1
        all_label_dfs.append(
            read_labels(labels_path, user_id)
        )

print('Total users with labels:', num_missed_labels)
print('Total trajectory files read:', len(all_traj_dfs))
print('Precentage of users with labels:',
      f"{(num_missed_labels/len(list(BASE_DIR.iterdir())))*100:.2f}%"
     )
#%%
# 
# 
# 
# after loading trajectories_df and labels_df
trajectories_df = pd.concat(all_traj_dfs, ignore_index=True)
if all_label_dfs:
    labels_df = pd.concat(all_label_dfs, ignore_index=True)
    labels_df.to_parquet(
        "/mnt/fastssd/mapedia_datasets/geolife/geolife_labels.parquet",
        engine="pyarrow",
        compression="snappy",
    )
    trajectories_df = trajectories_df.sort_values("timestamp")
    labels_df = pd.concat(all_label_dfs, ignore_index=True)
    labels_df = labels_df.sort_values("start_time")

    trajectories_df["transportation_mode"] = None

    for user_id, user_labels in tqdm(labels_df.groupby("user_id"), desc="Processing labels"):
        mask = trajectories_df["user_id"] == user_id
        user_traj = trajectories_df.loc[mask]

        for _, row in user_labels.iterrows():
            idx = user_traj[
                (user_traj["timestamp"] >= row.start_time) &
                (user_traj["timestamp"] <= row.end_time)
            ].index

            trajectories_df.loc[idx, "transportation_mode"] = row.transportation_mode


# -----------------------------
# Save to Parquet
# -----------------------------
trajectories_df.to_parquet(
    "/mnt/fastssd/mapedia_datasets/geolife/geolife_trajectories.parquet",
    engine="pyarrow",
    compression="snappy",
)



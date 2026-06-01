import pandas as pd
from shapely.geometry import LineString

# Load the CSV file
df = pd.read_csv("media/top_10_percentage.csv")

# Ensure timestamp is in datetime format
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Sort data by vehicle_id and timestamp
df = df.sort_values(by=["traj_id", "timestamp"])

# Group by vehicle_id and create a LineString for each vehicle
def create_linestring(group):
    points = list(zip(group["long"], group["lat"]))
    return LineString(points) if len(points) > 1 else None  # Only create LineString if more than 1 point

# Apply transformation
trajectories = df.groupby("traj_id").apply(create_linestring).reset_index(name="geometry")

# Save the output
trajectories.to_csv("media/converted_top_10_percentage.csv", index=False)  # Save as CSV

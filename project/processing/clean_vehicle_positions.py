import pandas as pd
from datetime import datetime, timezone
import os
import glob

def load_raw_positions(raw_dir="project/data/raw/mta/vehicle_positions"):
    files = glob.glob(f"{raw_dir}/**/*.pb", recursive=True)
    if not files:
        print("No raw position files found.")
        return pd.DataFrame()
    files.sort()
    latest = files[-1]
    print(f"Loading: {latest}")
    
    from google.transit import gtfs_realtime_pb2
    with open(latest, 'rb') as f:
        content = f.read()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
    
    records = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        if v.trip.route_id not in ["J", "Z"]:
            continue
        records.append({
            "vehicle_id": entity.id,
            "trip_id": v.trip.trip_id,
            "route_id": v.trip.route_id,
            "stop_id": v.stop_id,
            "current_stop_sequence": v.current_stop_sequence,
            "current_status": v.current_status,
            "occupancy_status": v.occupancy_status if v.HasField("occupancy_status") else None,
            "mta_timestamp": v.timestamp,
            "event_time": datetime.now(timezone.utc).isoformat()
        })
    return pd.DataFrame(records)

def derive_headway_gaps(df):
    """ 
    Occupancy proxy: derive the gap in seconds between consecutive trains arriving at the same stop on the same route. Smaller gaps suggest bunching (likely lower per-train occupancy); larger gaps suggest longer waits (like higher per-train occupancy).
    """
    if df.empty:
       return df
    df = df.sort_values(["route_id", "stop_id", "mta_timestamp"])
    
    df["headway_gap_sec"] = (
        df.groupby(["route_id", "stop_id"])["mta_timestamp"]
        .diff()    
        )
    return df

def classify_headway(seconds):
    if pd.isna(seconds):
        return "unknown"
    elif seconds < 300:
        return "bunched"
    elif seconds < 600:
        return "normal"
    else:
        return "sparse"

def clean_positions(df):
    if df.empty:
        return df
    
    df = derive_headway_gaps(df)
    df["headway_status"] = df["headway_gap_sec"].apply(classify_headway)
    df["event_time"] = pd.to_datetime(df["mta_timestamp"], unit='s', utc=True)
    df["window_start"] = df["event_time"].dt.floor("15min")
    return df

def saved_processed(df, output_dir="project/data/processed/vehicle_positions"):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = f"{output_dir}/positions_{ts}.parquet"
    df.to_parquet(path, index=False)
    print(f"Saved: {path}")
    return path

def main():
    df_raw = load_raw_positions()
    if df_raw.empty:
        print("No data to process.")
        return
    print(f"Raw records: {len(df_raw)}")
    df_clean = clean_positions(df_raw)
    print(f"Clean records: {len(df_clean)}")
    print(df_clean[["route_id", "stop_id", "headway_gap_sec", "headway_status", "window_start"]].head(10))
    path = saved_processed(df_clean)
    print(f"Done: {path}")

if __name__ == "__main__":
    main()
    
'''
Train bunching occurs when two or more transit vehicles (such as subways or buses) on the same route clump together instead of maintaining even spacing. This happens when a leading vehicle is delayed and the trailing vehicle catches up, leading to severe passenger crowding and wasted transit capacity.
'''

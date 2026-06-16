import pandas as pd
from datetime import datetime, timezone
import os
import glob

def load_raw_delays(raw_dir="project/data/raw/mta/trip_updates"):
    files = glob.glob(f"{raw_dir}/**/*.pb", recursive=True)
    if not files:
        print("No raw trip update files found")
        return pd.DataFrame()
    
    # read all parquet files if you saved as parquet, otherwise parse pb
    # assuming you saved decoded records as parquet in processing
    # for now load the most recent .pb and re-parse
    files.sort()
    latest = files[-1]
    print(f"Loading: {latest}")
    
    from google.transit import gtfs_realtime_pb2
    with open(latest, "rb") as f:
        content = f.read()
    
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
    
    records = []
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        trip = entity.trip_update
        if trip.trip.route_id not in ["J", "Z"]:
            continue
        for stu in trip.stop_time_update:
            records.append({
                "vehicle_id": entity.id,
                "trip_id": trip.trip.trip_id,
                "route_id": trip.trip.route_id,
                "stop_id": stu.stop_id,
                "arrival_delay": stu.arrival.delay if stu.HasField("arrival") else None,
                "departure_delay": stu.departure.delay if stu.HasField("departure") else None,
                "event_time": datetime.now(timezone.utc).isoformat()
            })
    return pd.DataFrame(records)

def clean_delays(df):
    if df.empty:
        return df

    # drop rows where both delays are null — no useful signal
    df = df.dropna(subset=["arrival_delay", "departure_delay"], how="all")

    # fill remaining nulls with 0 — if one exists, treat missing as on time
    df["arrival_delay"] = df["arrival_delay"].fillna(0).astype(int)
    df["departure_delay"] = df["departure_delay"].fillna(0).astype(int)

    # derive delay severity label
    df["delay_severity"] = df["arrival_delay"].apply(classify_delay)

    # parse event_time to datetime
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True)

    # add 15-min window column for later join
    df["window_start"] = df["event_time"].dt.floor("15min")

    return df

def classify_delay(seconds):
    if seconds <= 60:
        return "on_time"
    elif seconds <= 300:
        return "minor"       # 1-5 min
    elif seconds <= 600:
        return "moderate"    # 5-10 min
    else:
        return "severe"      # 10+ min

def save_processed(df, output_dir="project/data/processed/delays"):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = f"{output_dir}/delays_{ts}.parquet"
    df.to_parquet(path, index=False)
    print(f"Saved: {path}")
    return path

def main():
    df_raw = load_raw_delays()
    if df_raw.empty:
        print("No data to process")
        return

    print(f"Raw records: {len(df_raw)}")
    df_clean = clean_delays(df_raw)
    print(f"Clean records: {len(df_clean)}")
    print(df_clean[["route_id", "stop_id", "arrival_delay", "delay_severity", "window_start"]].head())
    path = save_processed(df_clean)
    print(f"Done: {path}")

if __name__ == "__main__":
    main()
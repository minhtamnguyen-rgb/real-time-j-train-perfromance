import pandas as pd
from datetime import datetime, timezone
import os
import glob
from google.transit import gtfs_realtime_pb2

def load_raw_delays(raw_dir="project/data/raw/mta/trip_updates"):
    files = glob.glob(f"{raw_dir}/**/*.pb", recursive=True)
    if not files:
        print("No raw trip update files found")
        return pd.DataFrame()

    print(f"Found {len(files)} raw files")

    all_records = []
    for file_path in files:
        with open(file_path, "rb") as f:
            content = f.read()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(content)

        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue
            trip = entity.trip_update
            if trip.trip.route_id not in ["J", "Z"]:
                continue
            for stu in trip.stop_time_update:
                all_records.append({
                    "vehicle_id": entity.id,
                    "trip_id": trip.trip.trip_id,
                    "route_id": trip.trip.route_id,
                    "stop_id": stu.stop_id,
                    "arrival_delay": stu.arrival.delay if stu.HasField("arrival") else None,
                    "departure_delay": stu.departure.delay if stu.HasField("departure") else None,
                    "source_file": file_path,
                    "event_time": datetime.now(timezone.utc).isoformat()
                })

    return pd.DataFrame(all_records)

def clean_delays(df):
    if df.empty:
        return df

    df = df.dropna(subset=["arrival_delay", "departure_delay"], how="all")
    df["arrival_delay"] = df["arrival_delay"].fillna(0).astype(int)
    df["departure_delay"] = df["departure_delay"].fillna(0).astype(int)
    df["delay_severity"] = df["arrival_delay"].apply(classify_delay)
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True)
    df["window_start"] = df["event_time"].dt.floor("15min")

    # drop exact duplicate rows in case the same .pb is processed more than once
    df = df.drop_duplicates(subset=["vehicle_id", "trip_id", "stop_id", "source_file"])

    return df

def classify_delay(seconds):
    if seconds <= 60:
        return "on_time"
    elif seconds <= 300:
        return "minor"
    elif seconds <= 600:
        return "moderate"
    else:
        return "severe"

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
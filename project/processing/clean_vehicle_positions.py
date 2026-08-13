import pandas as pd
from datetime import datetime, timezone
import os
import glob
from google.transit import gtfs_realtime_pb2

def load_raw_positions(raw_dir="project/data/raw/mta/vehicle_positions"):
    files = glob.glob(f"{raw_dir}/**/*.pb", recursive=True)
    if not files:
        print("No raw vehicle position files found")
        return pd.DataFrame()

    print(f"Found {len(files)} raw files")

    all_records = []
    for file_path in files:
        with open(file_path, "rb") as f:
            content = f.read()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(content)

        for entity in feed.entity:
            if not entity.HasField("vehicle"):
                continue
            v = entity.vehicle
            if v.trip.route_id not in ["J", "Z"]:
                continue
            all_records.append({
                "vehicle_id": entity.id,
                "trip_id": v.trip.trip_id,
                "route_id": v.trip.route_id,
                "stop_id": v.stop_id,
                "current_stop_sequence": v.current_stop_sequence,
                "current_status": v.current_status,
                "occupancy_status": v.occupancy_status if v.HasField("occupancy_status") else None,
                "mta_timestamp": v.timestamp,
                "source_file": file_path,
                "event_time": datetime.now(timezone.utc).isoformat()
            })

    return pd.DataFrame(all_records)

def derive_headway_gaps(df):
    if df.empty:
        return df

    df = df.sort_values(["route_id", "stop_id", "mta_timestamp"])
    df["headway_gap_sec"] = (
        df.groupby(["route_id", "stop_id"])["mta_timestamp"].diff()
    )

    # discard nonsensical gaps — real J/Z headways are never more than ~30 min
    df.loc[df["headway_gap_sec"] > 1800, "headway_gap_sec"] = None

    return df

def classify_headway(seconds):
    if pd.isna(seconds):
        return "unknown"
    elif seconds <= 300:
        return "bunched"
    elif seconds <= 600:
        return "normal"
    else:
        return "sparse"

def clean_positions(df):
    if df.empty:
        return df

    df = df.drop_duplicates(subset=["vehicle_id", "trip_id", "stop_id", "mta_timestamp"])
    df = derive_headway_gaps(df)
    df["headway_status"] = df["headway_gap_sec"].apply(classify_headway)
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True)
    df["mta_timestamp"] = pd.to_datetime(df["mta_timestamp"], unit="s", utc=True)
    df["window_start"] = df["event_time"].dt.floor("15min")

    return df

def save_processed(df, output_dir="project/data/processed/vehicle_positions"):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    final_path = f"{output_dir}/positions_{ts}.parquet"
    tmp_path = f"{final_path}.tmp"
    try:
        df.to_parquet(tmp_path, index=False)
        import duckdb
        con = duckdb.connect()
        count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{tmp_path}')").fetchone()[0]
        con.close()
        if count != len(df):
            raise ValueError(f"Validation failed: wrote {len(df)} rows but parquet has {count}")
        os.rename(tmp_path, final_path)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e
    print(f"Saved: {final_path}")
    return final_path

def main():
    df_raw = load_raw_positions()
    if df_raw.empty:
        print("No data to process")
        return

    print(f"Raw records: {len(df_raw)}")
    df_clean = clean_positions(df_raw)
    print(f"Clean records: {len(df_clean)}")
    print(df_clean[["route_id", "stop_id", "headway_gap_sec", "headway_status", "window_start"]].head(10))
    path = save_processed(df_clean)
    print(f"Done: {path}")
    import sys
    sys.path.insert(0, '.')
    from project.storage import upload_file
    upload_file(path, path.replace("project/", ""))

if __name__ == "__main__":
    main()
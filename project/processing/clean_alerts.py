import pandas as pd
from datetime import datetime, timezone
import os
import glob
from google.transit import gtfs_realtime_pb2

EFFECT_LABELS = {
    1: "no_service", 2: "reduced_service", 3: "significant_delays",
    4: "detour", 5: "additional_service", 6: "modified_service",
    7: "other_effect", 8: "unknown_effect", 9: "stop_moved",
    10: "no_effect", 11: "accessibility_issue",
}

def load_raw_alerts(raw_dir="project/data/raw/mta/alerts"):
    files = glob.glob(f"{raw_dir}/**/*.pb", recursive=True)
    if not files:
        print("No raw alert files found")
        return pd.DataFrame()

    print(f"Found {len(files)} raw files")

    all_records = []
    for file_path in files:
        with open(file_path, "rb") as f:
            content = f.read()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(content)

        for entity in feed.entity:
            if not entity.HasField("alert"):
                continue
            alert = entity.alert
            route_ids = list(set(
                e.route_id for e in alert.informed_entity if e.route_id in ["J", "Z"]
            ))
            if not route_ids:
                continue

            header = alert.header_text.translation[0].text if alert.header_text.translation else ""
            description = alert.description_text.translation[0].text if alert.description_text.translation else ""

            all_records.append({
                "alert_id": entity.id,
                "route_ids": route_ids,
                "header": header,
                "description": description,
                "effect": alert.effect,
                "start_time": alert.active_period[0].start if alert.active_period else None,
                "end_time": alert.active_period[0].end if alert.active_period and alert.active_period[0].HasField("end") else None,
                "source_file": file_path,
                "event_time": datetime.now(timezone.utc).isoformat()
            })

    return pd.DataFrame(all_records)

def clean_alerts(df):
    if df.empty:
        return df

    df["severity"] = df["effect"].map(EFFECT_LABELS).fillna("unknown_effect")
    df["start_time"] = pd.to_datetime(df["start_time"], unit="s", utc=True, errors="coerce")
    df["end_time"] = pd.to_datetime(df["end_time"], unit="s", utc=True, errors="coerce")
    df["description_short"] = df["description"].str.slice(0, 200)
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True)
    df["window_start"] = df["event_time"].dt.floor("15min")

    df = df.drop_duplicates(subset=["alert_id", "source_file"])

    return df

def save_processed(df, output_dir="project/data/processed/alerts"):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    final_path = f"{output_dir}/alerts_{ts}.parquet"
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
    df_raw = load_raw_alerts()
    if df_raw.empty:
        print("No data to process")
        return

    print(f"Raw records: {len(df_raw)}")
    df_clean = clean_alerts(df_raw)
    print(f"Clean records: {len(df_clean)}")
    print(df_clean[["route_ids", "header", "severity", "start_time", "end_time"]].head())
    path = save_processed(df_clean)
    print(f"Done: {path}")
    import sys
    sys.path.insert(0, '.')
    from project.storage import upload_file
    upload_file(path, path.replace("project/", ""))
if __name__ == "__main__":
    main()
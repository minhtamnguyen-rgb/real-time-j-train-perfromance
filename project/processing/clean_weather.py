import pandas as pd
import json
from datetime import datetime, timezone
import os
import glob

def load_raw_weather(raw_dir="project/data/raw/weather"):
    import sys
    sys.path.insert(0, '.')
    from project.storage import sync_from_r2
    sync_from_r2("data/raw/weather/", raw_dir)

    files = glob.glob(f"{raw_dir}/**/*.json", recursive=True)
    if not files:
        print("No raw weather files found")
        return pd.DataFrame()

    print(f"Found {len(files)} raw files")

    all_records = []
    for file_path in files:
        with open(file_path, "r") as f:
            data = json.load(f)

        if "hourly" in data:
            hourly = data["hourly"]
            for i, t in enumerate(hourly["time"]):
                all_records.append({
                    "temperature_c":     hourly["temperature_2m"][i],
                    "humidity_pct":      hourly["relative_humidity_2m"][i],
                    "precip_mm":         hourly["precipitation"][i],
                    "snowfall_cm":       hourly["snowfall"][i],
                    "wind_speed_kmh":    hourly["wind_speed_10m"][i],
                    "weather_timestamp": t,
                    "source_file":       file_path,
                    "event_time":        datetime.now(timezone.utc).isoformat()
                })
        elif "current" in data:
            current = data["current"]
            all_records.append({
                "temperature_c":     current["temperature_2m"],
                "humidity_pct":      current["relative_humidity_2m"],
                "precip_mm":         current["precipitation"],
                "snowfall_cm":       current["snowfall"],
                "wind_speed_kmh":    current["wind_speed_10m"],
                "weather_timestamp": current["time"],
                "source_file":       file_path,
                "event_time":        datetime.now(timezone.utc).isoformat()
            })

    return pd.DataFrame(all_records)

def clean_weather(df):
    if df.empty:
        return df

    df["weather_timestamp"] = pd.to_datetime(df["weather_timestamp"])
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True, format='ISO8601')
    df["window_start"] = df["event_time"].dt.floor("15min")
    
    # force obs_hour to UTC timezone-aware
    df["obs_hour"] = pd.to_datetime(df["weather_timestamp"]).dt.floor("h").dt.tz_localize("UTC")
    
    df["is_extreme_heat"] = df["temperature_c"] >= 32.2
    df["is_precip"] = df["precip_mm"] > 0
    df["is_snow"] = df["snowfall_cm"] > 0

    df = df.drop_duplicates(subset=["weather_timestamp", "source_file"])

    return df

def save_processed(df, output_dir="project/data/processed/weather"):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    final_path = f"{output_dir}/weather_{ts}.parquet"
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
    df_raw = load_raw_weather()
    if df_raw.empty:
        print("No data to process")
        return

    print(f"Raw records: {len(df_raw)}")
    df_clean = clean_weather(df_raw)
    print(f"Clean records: {len(df_clean)}")
    print(df_clean[["temperature_c", "humidity_pct", "precip_mm", "is_extreme_heat", "obs_hour"]].head())
    path = save_processed(df_clean)
    print(f"Done: {path}")
    import sys
    sys.path.insert(0, '.')
    from project.storage import upload_file
    upload_file(path, path.replace("project/", ""))

if __name__ == "__main__":
    main()

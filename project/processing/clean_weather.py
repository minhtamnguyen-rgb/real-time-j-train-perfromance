import pandas as pd
import json
from datetime import datetime, timezone
import os
import glob

def load_raw_weather(raw_dir="project/data/raw/weather"):
    files = glob.glob(f"{raw_dir}/**/*.json", recursive=True)
    if not files:
        print("No raw weather files found")
        return pd.DataFrame()

    print(f"Found {len(files)} raw files")

    all_records = []
    for file_path in files:
        with open(file_path, "r") as f:
            data = json.load(f)

        current = data["current"]
        all_records.append({
            "temperature_c": current["temperature_2m"],
            "humidity_pct": current["relative_humidity_2m"],
            "precip_mm": current["precipitation"],
            "snowfall_cm": current["snowfall"],
            "wind_speed_kmh": current["wind_speed_10m"],
            "weather_timestamp": current["time"],
            "source_file": file_path,
            "event_time": datetime.now(timezone.utc).isoformat()
        })

    return pd.DataFrame(all_records)

def clean_weather(df):
    if df.empty:
        return df

    df["weather_timestamp"] = pd.to_datetime(df["weather_timestamp"])
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True)
    df["window_start"] = df["event_time"].dt.floor("15min")
    df["obs_hour"] = df["event_time"].dt.floor("h")
    df["is_extreme_heat"] = df["temperature_c"] >= 32.2
    df["is_precip"] = df["precip_mm"] > 0
    df["is_snow"] = df["snowfall_cm"] > 0

    df = df.drop_duplicates(subset=["weather_timestamp", "source_file"])

    return df

def save_processed(df, output_dir="project/data/processed/weather"):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = f"{output_dir}/weather_{ts}.parquet"
    df.to_parquet(path, index=False)
    print(f"Saved: {path}")
    return path

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

if __name__ == "__main__":
    main()
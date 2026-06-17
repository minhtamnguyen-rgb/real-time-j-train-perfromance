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
    files.sort()
    latest = files[-1]
    print(f"Loading: {latest}")

    with open(latest, "r") as f:
        data = json.load(f)

    current = data["current"]
    record = {
        "temperature_c": current["temperature_2m"],
        "humidity_pct": current["relative_humidity_2m"],
        "precip_mm": current["precipitation"],
        "snowfall_cm": current["snowfall"],
        "wind_speed_kmh": current["wind_speed_10m"],
        "weather_timestamp": current["time"],
        "event_time": datetime.now(timezone.utc).isoformat()
    }
    return pd.DataFrame([record])
def clean_weather(df):
    if df.empty:
        return df_clean
    
    #weather_timesamp if local NYC time (America/New_York) wihout tz info
    df["weather_timestamp"] = pd.to_datetime(df["weather_timestamp"])
    
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True)
    
    #align to 15-min window for join with transit data
    df["window_start"] = df["event_time"].dt.floor("15min")
    
    #derive obs_hour for hourly join key
    df["obs_hour"] = df["event_time"].dt.floor("h")
    
    #flag extreme condition for dashboard thresholds
    df["is_extreme_heat"] = df["temperature_c"] >= 39.2
    df["is_precip"] = df["precip_mm"] > 0
    df["is_snow"] = df["snowfall_cm"] > 0
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
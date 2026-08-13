import requests
import json
import os
from datetime import datetime, timezone

URL = 'https://api.open-meteo.com/v1/forecast'

PARAMS = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "hourly": [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "snowfall",
        "wind_speed_10m"
    ],
    "timezone": "America/New_York",
    "forecast_days": 1,
    "past_days": 1      # get yesterday + today so no gaps between polls
}

def fetch_weather():
    response = requests.get(URL, params=PARAMS, timeout=30)
    response.raise_for_status()
    return response.json()

def save_raw(data):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = f"project/data/raw/weather/weather_{ts}.json"
    tmp_path = f"{path}.tmp"
    os.makedirs("project/data/raw/weather", exist_ok=True)
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        os.rename(tmp_path, path)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e
    return path

def extract_hourly(data):
    hourly = data["hourly"]
    records = []
    times = hourly["time"]
    for i, t in enumerate(times):
        records.append({
            "temperature_c":    hourly["temperature_2m"][i],
            "humidity_pct":     hourly["relative_humidity_2m"][i],
            "precip_mm":        hourly["precipitation"][i],
            "snowfall_cm":      hourly["snowfall"][i],
            "wind_speed_kmh":   hourly["wind_speed_10m"][i],
            "weather_timestamp": t,
            "event_time":       datetime.now(timezone.utc).isoformat()
        })
    return records

def main():
    data = fetch_weather()
    raw_path = save_raw(data)
    records = extract_hourly(data)
    precip_hours = sum(1 for r in records if r["precip_mm"] > 0)
    print(f"Saved: {raw_path}")
    print(f"Hourly records: {len(records)}, hours with precipitation: {precip_hours}")
    for r in records[-3:]:
        print(r)

    import sys
    sys.path.insert(0, '.')
    from project.storage import upload_file
    upload_file(raw_path, raw_path.replace("project/", ""))

if __name__ == "__main__":
    main()
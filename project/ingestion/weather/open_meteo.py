#!/usr/bin/env python
# coding: utf-8

# In[15]:


import requests
import json
import os
from datetime import datetime, timezone


# In[16]:


url = 'https://api.open-meteo.com/v1/forecast'


# In[17]:


PARAMS = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "current": [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "snowfall",
        "wind_speed_10m"
    ],
    "timezone": "America/New_York",
    "forecast_days": 1
}


# In[18]:


def fetch_weather():
    response = requests.get(url, params = PARAMS, timeout = 10)
    response.raise_for_status()
    return response.json()


# In[19]:


def save_raw(data):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = f"data/raw/weather/weather_{ts}.json"
    os.makedirs("data/raw/weather", exist_ok = True)
    with open(path, "w") as f:
        json.dump(data, f)
    return path


# In[20]:


def extract_current(data):
    current = data["current"]
    return {
        "temperature_c": current["temperature_2m"],
        "humidity_pct": current["relative_humidity_2m"],
        "precip_mm": current["precipitation"],
        "snowfall_cm": current["snowfall"],
        "wind_speed_kmh": current["wind_speed_10m"],
        "weather_timestamp": current["time"],         # Open-Meteo's own timestamp
        "event_time": datetime.now(timezone.utc).isoformat()
    }


# In[21]:


def main():
    data = fetch_weather()
    raw_path = save_raw(data)
    record = extract_current(data)
    print(f"Saved: {raw_path}")
    print(record)

if __name__ == "__main__":
    main()


# In[23]:


main()


# In[ ]:





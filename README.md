# MTA Weather Pipeline

Real-time monitoring of J/Z line performance correlated with weather conditions.

## Question
**How does weather impact subway reliability on the J/Z line?**

## Architecture

Two independent data streams joined at the feature layer.


```

mta-weather/
│
├── ingestion/
│   ├── mta/
│   │   ├── trip_updates.py        # J/Z delays per stop
│   │   ├── alerts.py              # Service alerts affecting J/Z
│   │   └── vehicle_positions.py   # Train positions + headways
│   └── weather/
│       └── open_meteo.py          # Temperature, precipitation, humidity
│
├── processing/
│   ├── clean_delays.py            # Normalize delay data, handle nulls
│   ├── clean_alerts.py            # Severity mapping
│   └── clean_weather.py           # Align to 15-min windows
│
├── features/
│   └── jz_weather_correlation.py  # Join transit + weather at route/hour grain
│
├── data/
│   ├── raw/
│   │   ├── mta/
│   │   │   ├── trip_updates/      # Raw protobuf (.pb)
│   │   │   ├── alerts/            # Raw protobuf (.pb)
│   │   │   └── vehicle_positions/ # Raw protobuf (.pb)
│   │   └── weather/               # Raw JSON responses
│   ├── processed/
│   │   ├── delays/                # Parquet
│   │   ├── alerts/                # Parquet
│   │   └── weather/               # Parquet
│   └── features/
│       └── jz_combined/           # Final feature table, Parquet
│
├── notebooks/
│   └── exploration.ipynb          # Prototyping and EDA
│
└── README.md


## Stack

| Layer | Tool |
|---|---|
| Ingestion | Python, requests, gtfs-realtime-bindings |
| Scheduling | Prefect |
| Raw storage | Local filesystem → Cloudflare R2 |
| Processing | pandas |
| Analytics | DuckDB |
| Transformations | dbt Core |
| Dashboard | Streamlit |
| Version control | GitHub |

## Data Model

One row = one J/Z train, one stop, one 15-minute window.


## Streams

**Transit (MTA GTFS-RT)**
- Trip updates — arrival/departure delay per stop in seconds
- Alerts — service changes, disruptions, severity
- Vehicle positions — train locations, headway gaps

**Weather (Open-Meteo)**
- Temperature (°C)
- Precipitation (mm)
- Humidity (%)
- Wind speed

## Join Key

```sql
date_trunc('hour', window_start) = weather.obs_hour
AND route_id IN ('J', 'Z')
```

## Setup

```bash
pip install requests gtfs-realtime-bindings pandas pyarrow duckdb prefect
```

Add your MTA API key as an environment variable:

```bash
export MTA_API_KEY=your_key_here
```

## Status
- [x] Trip updates ingestion
- [x] Alerts ingestion
- [ ] Vehicle positions ingestion
- [ ] Weather ingestion
- [ ] Processing layer
- [ ] Feature layer
- [ ] Dashboard

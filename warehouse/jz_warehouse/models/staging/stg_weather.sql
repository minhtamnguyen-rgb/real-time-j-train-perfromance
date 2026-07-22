{{ config(materialized='view') }}

with processed as (
    select *
    from read_parquet('/workspaces/real-time-j-train-perfromance/project/data/processed/weather/*.parquet')
),

deduped as (
    select
        temperature_c,
        humidity_pct,
        precip_mm,
        snowfall_cm,
        wind_speed_kmh,
        weather_timestamp,
        obs_hour,
        is_extreme_heat,
        is_precip,
        is_snow,
        row_number() over (
            partition by obs_hour
            order by weather_timestamp desc    -- use Open-Meteo's own timestamp
        )                               as rn
    from processed
)

select
    temperature_c,
    humidity_pct,
    precip_mm,
    snowfall_cm,
    wind_speed_kmh,
    weather_timestamp,
    obs_hour,
    is_extreme_heat,
    is_precip,
    is_snow
from deduped
where rn = 1
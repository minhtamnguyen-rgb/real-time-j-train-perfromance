{{ config(materialized='table') }}

with weather as (
    select * from {{ ref('stg_weather') }}
),

bucketed as (
    select
        obs_hour,
        temperature_c,
        humidity_pct,
        precip_mm,
        snowfall_cm,
        wind_speed_kmh,
        is_extreme_heat,
        is_precip,
        is_snow,

        -- weather condition bucket for grouping
        case
            when snowfall_cm > 0                        then 'snow'
            when precip_mm > 5                          then 'heavy_rain'
            when precip_mm > 0                          then 'light_rain'
            when temperature_c >= 32.2                  then 'extreme_heat'
            when temperature_c >= 27                    then 'hot'
            when temperature_c <= 0                     then 'freezing'
            else                                             'mild'
        end                                             as condition_bucket,

        -- heat index proxy (simplified)
        case
            when temperature_c >= 27 and humidity_pct >= 60
            then round(temperature_c + (humidity_pct - 60) * 0.1, 1)
            else temperature_c
        end                                             as feels_like_c,

        -- wind category
        case
            when wind_speed_kmh >= 60                   then 'strong'
            when wind_speed_kmh >= 30                   then 'moderate'
            else                                             'light'
        end                                             as wind_category

    from weather
)

select * from bucketed

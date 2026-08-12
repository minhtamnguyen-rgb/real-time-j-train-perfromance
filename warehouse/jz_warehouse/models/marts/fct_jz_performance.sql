{{ config(materialized='table') }}

with delays AS (
    SELECT
        route_id,
        window_start,
        AVG(arrival_delay)          AS avg_delay_sec,
        MAX(arrival_delay)          AS max_delay_sec,
        COUNT(*)                    AS delay_records,
        COUNT(CASE WHEN delay_severity = 'severe'   THEN 1 END) AS severe_count,
        COUNT(CASE WHEN delay_severity = 'moderate' THEN 1 END) AS moderate_count,
        COUNT(CASE WHEN delay_severity = 'minor'    THEN 1 END) AS minor_count,
        COUNT(CASE WHEN delay_severity = 'on_time'  THEN 1 END) AS on_time_count
    FROM {{ ref('stg_delays') }}
    GROUP BY route_id, window_start
),

worst_stop as (
    SELECT DISTINCT ON (route_id, window_start)
        route_id,
        window_start,
        stop_id     AS worst_stop_id,
        stop_name   AS worst_stop_name
    FROM {{ ref('stg_delays') }}
    WHERE arrival_delay IS NOT NULL
    ORDER BY route_id, window_start, arrival_delay DESC
),

alerts as (
    select
        route_id,
        window_start,
        count(distinct alert_id)    as alerts_active,
        max(severity)               as worst_severity,
        string_agg(distinct header, ' | ')  as alert_headers
    from {{ ref('stg_alerts') }}
    group by route_id, window_start
),

positions as (
    select
        route_id,
        window_start,
        avg(headway_gap_sec)        as avg_headway_gap_sec,
        max(headway_gap_sec)        as max_headway_gap_sec,
        count(case when occupancy_proxy = 'bunched' then 1 end) as bunched_count,
        count(case when occupancy_proxy = 'sparse'  then 1 end) as sparse_count
    from {{ ref('stg_positions') }}
    group by route_id, window_start
),

weather as (
    select
        obs_hour,
        temperature_c,
        humidity_pct,
        precip_mm,
        snowfall_cm,
        wind_speed_kmh,
        is_extreme_heat,
        is_precip,
        is_snow
    from {{ ref('stg_weather') }}
)

select
    d.route_id,
    d.window_start,
    ws.worst_stop_name,
    ws.worst_stop_id,
    d.avg_delay_sec,
    d.max_delay_sec,
    d.delay_records,
    d.severe_count,
    d.moderate_count,
    d.minor_count,
    d.on_time_count,
    round(
        cast(d.severe_count + d.moderate_count as double) / nullif(d.delay_records, 0) * 100,
        2
    )                               as pct_delayed,
    coalesce(a.alerts_active, 0)    as alerts_active,
    a.worst_severity,
    a.alert_headers,
    p.avg_headway_gap_sec,
    p.max_headway_gap_sec,
    p.bunched_count,
    p.sparse_count,
    w.temperature_c,
    w.humidity_pct,
    w.precip_mm,
    w.snowfall_cm,
    w.wind_speed_kmh,
    w.is_extreme_heat,
    w.is_precip,
    w.is_snow,
    current_timestamp as dbt_updated_at
from delays d
left join worst_stop ws
    on  d.route_id     = ws.route_id
    and d.window_start = ws.window_start
left join alerts a
    on  d.route_id     = a.route_id
    and d.window_start = a.window_start
left join positions p
    on  d.route_id     = p.route_id
    and d.window_start = p.window_start
left join weather w
    on date_trunc('hour', d.window_start) = w.obs_hour
order by d.window_start desc
{{ config(materialized='table') }}

with alerts as (
    select * from {{ ref('stg_alerts') }}
),

current_alerts as (
    select
        alert_id,
        route_id,
        header,
        description_short,
        severity,
        start_time,
        end_time,
        window_start,

        -- flag currently active (no end time means still active)
        case
            when end_time is null                                       then true
            when end_time > (current_timestamp at time zone 'UTC')     then true
            else                                                             false
        end                                                             as is_currently_active,
        -- how long has this alert been active
        case
            when start_time is not null
            then extract(epoch from (current_timestamp - start_time)) / 3600
            else null
        end                                             as hours_active

    from alerts
)

select * from current_alerts
where is_currently_active = true

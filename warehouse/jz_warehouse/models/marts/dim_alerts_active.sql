{{ config(materialized='view') }}

with alerts as (
    select * from {{ ref('stg_alerts') }}
),

classified as (
    select
        alert_id,
        route_id,
        header,
        description_short,
        severity,
        start_time,
        end_time,
        window_start,

        -- alert status
        case
            when start_time > current_timestamp                     then 'upcoming'
            when end_time is null                                   then 'ongoing'
            when end_time > current_timestamp                       then 'active'
            else                                                         'expired'
        end                                                         as alert_status,

        -- time metrics
        extract(epoch from (current_timestamp - start_time)) / 3600    as hours_since_start,
        extract(epoch from (start_time - current_timestamp)) / 3600    as hours_until_start,

        -- is this worth showing
        case
            when start_time > current_timestamp                     then true  -- upcoming
            when end_time is null                                   then true  -- ongoing
            when end_time > current_timestamp                       then true  -- still active
            else                                                        false  -- expired
        end                                                         as is_relevant

    from alerts
)

select
    alert_id,
    route_id,
    header,
    description_short,
    severity,
    start_time,
    end_time,
    alert_status,
    hours_since_start,
    hours_until_start,
    window_start
from classified
where is_relevant = true
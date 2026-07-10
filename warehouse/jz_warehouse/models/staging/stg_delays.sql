{{ config(materialized='view') }}

with processed as (
    select *
    from read_parquet('/workspaces/real-time-j-train-perfromance/project/data/processed/delays/*.parquet')
),

cleaned as (
    select
        vehicle_id,
        trip_id,
        route_id,
        stop_id,
        coalesce(arrival_delay, 0) as arrival_delay,
        coalesce(departure_delay, 0) as departure_delay,
        source_file,
        event_time,
        window_start,
        case
            when coalesce(arrival_delay, 0) <= 60  then 'on_time'
            when coalesce(arrival_delay, 0) <= 300 then 'minor'
            when coalesce(arrival_delay, 0) <= 600 then 'moderate'
            else 'severe'
        end                                     as delay_severity,
        row_number() over (
            partition by vehicle_id, trip_id, stop_id, source_file
            order by event_time
        )                                       as rn
    from processed
    where arrival_delay is not null
       or departure_delay is not null
)

select
    vehicle_id,
    trip_id,
    route_id,
    stop_id,
    arrival_delay,
    departure_delay,
    delay_severity,
    source_file,
    event_time,
    window_start
from cleaned
where rn = 1

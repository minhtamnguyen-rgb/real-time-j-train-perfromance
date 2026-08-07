{{ config(materialized='view') }}

with processed as (
    select *
    from read_parquet('/workspaces/real-time-j-train-perfromance/project/data/processed/delays/*.parquet')
),

stops as (
    select * from {{ ref('jz_stops') }}
),

cleaned as (
    select
        p.vehicle_id,
        p.trip_id,
        p.route_id,
        p.stop_id,
        s.stop_name,
        s.direction,
        coalesce(p.arrival_delay, 0)            as arrival_delay,
        coalesce(p.departure_delay, 0)          as departure_delay,
        p.source_file,
        p.event_time,
        p.window_start,
        case
            when coalesce(p.arrival_delay, 0) <= 60  then 'on_time'
            when coalesce(p.arrival_delay, 0) <= 300 then 'minor'
            when coalesce(p.arrival_delay, 0) <= 600 then 'moderate'
            else 'severe'
        end                                     as delay_severity,
        row_number() over (
            partition by p.vehicle_id, p.trip_id, p.stop_id, p.source_file
            order by p.event_time
        )                                       as rn
    from processed p
    left join stops s on p.stop_id = s.stop_id
    where p.arrival_delay is not null
       or p.departure_delay is not null
)

select
    vehicle_id,
    trip_id,
    route_id,
    stop_id,
    stop_name,
    direction,
    arrival_delay,
    departure_delay,
    delay_severity,
    source_file,
    event_time,
    window_start
from cleaned
where rn = 1
{{ config(materialized='view') }}

with processed as (
    select *
    from read_parquet('/workspaces/real-time-j-train-perfromance/project/data/processed/vehicle_positions/*.parquet')
),

deduped as (
    select
        vehicle_id,
        trip_id,
        route_id,
        stop_id,
        current_stop_sequence,
        current_status,
        mta_timestamp,
        headway_gap_sec,
        headway_status,
        window_start,
        row_number() over (
            partition by vehicle_id, trip_id, stop_id, mta_timestamp
            order by event_time desc
        )                               as rn
    from processed
    where route_id in ('J', 'Z')
      and (headway_gap_sec is null or headway_gap_sec <= 1800)  -- cap outliers
),

with_occupancy_proxy as (
    select
        vehicle_id,
        trip_id,
        route_id,
        stop_id,
        current_stop_sequence,
        current_status,
        mta_timestamp,
        headway_gap_sec,
        headway_status,
        window_start,

        -- occupancy proxy label based on headway
        case
            when headway_gap_sec is null        then 'unknown'
            when headway_gap_sec <= 300         then 'bunched'
            when headway_gap_sec <= 600         then 'normal'
            else                                     'sparse'
        end                                     as occupancy_proxy
    from deduped
    where rn = 1
)

select * from with_occupancy_proxy
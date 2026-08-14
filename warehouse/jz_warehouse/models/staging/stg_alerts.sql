{{ config(materialized='view') }}

with processed as (
    select *
    from read_parquet('s3://jz-pipeline/data/processed/alerts/*.parquet')
),

unnested as (
    select
        alert_id,
        unnest(route_ids)               as route_id,
        header,
        description,
        description_short,
        effect,
        severity,
        start_time,
        end_time,
        source_file,
        event_time,
        window_start
    from processed
),

deduped as (
    select
        alert_id,
        route_id,
        header,
        description_short,
        severity,
        start_time,
        end_time,
        window_start,
        row_number() over (
            partition by alert_id, route_id
            order by event_time desc
        )                               as rn
    from unnested
    where route_id in ('J', 'Z')
)

select
    alert_id,
    route_id,
    header,
    description_short,
    severity,
    start_time,
    end_time,
    window_start
from deduped
where rn = 1
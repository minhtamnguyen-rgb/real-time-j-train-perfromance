import duckdb
import os
from datetime import datetime, timezone

def build_features(
    delays_dir="project/data/processed/delays",
    alerts_dir="project/data/processed/alerts",
    weather_dir="project/data/processed/weather",
    positions_dir="project/data/processed/vehicle_positions",
    output_dir="project/data/features/jz_combined"
):
    con = duckdb.connect()

    query = f"""
    WITH delays AS (
        SELECT
            route_id,
            window_start,
            AVG(arrival_delay) AS avg_delay_sec,
            MAX(arrival_delay) AS max_delay_sec,
            COUNT(*) AS delay_records
        FROM read_parquet('{delays_dir}/*.parquet')
        GROUP BY route_id, window_start
    ),
    alerts AS (
        SELECT
            route_id,
            window_start,
            COUNT(DISTINCT alert_id) AS alerts_active
        FROM (
            SELECT unnest(route_ids) AS route_id, window_start, alert_id
            FROM read_parquet('{alerts_dir}/*.parquet')
        )
        GROUP BY route_id, window_start
    ),
    positions AS (
        SELECT
            route_id,
            window_start,
            AVG(headway_gap_sec) AS avg_headway_gap_sec,
            MAX(headway_gap_sec) AS max_headway_gap_sec
        FROM read_parquet('{positions_dir}/*.parquet')
        GROUP BY route_id, window_start
    ),
    weather_deduped AS (
        SELECT DISTINCT ON (obs_hour)
            obs_hour,
            temperature_c,
            humidity_pct,
            precip_mm,
            snowfall_cm,
            wind_speed_kmh,
            is_extreme_heat,
            is_precip,
            is_snow
        FROM read_parquet('{weather_dir}/*.parquet')
        ORDER BY obs_hour, event_time DESC
    )

    SELECT
        d.route_id,
        d.window_start,
        d.avg_delay_sec,
        d.max_delay_sec,
        d.delay_records,
        COALESCE(a.alerts_active, 0) AS alerts_active,
        p.avg_headway_gap_sec,
        p.max_headway_gap_sec,
        w.temperature_c,
        w.humidity_pct,
        w.precip_mm,
        w.snowfall_cm,
        w.wind_speed_kmh,
        w.is_extreme_heat,
        w.is_precip,
        w.is_snow
    FROM delays d
    LEFT JOIN alerts a
        ON d.route_id = a.route_id
        AND d.window_start = a.window_start
    LEFT JOIN positions p
        ON d.route_id = p.route_id
        AND d.window_start = p.window_start
    LEFT JOIN weather_deduped w
        ON date_trunc('hour', d.window_start) = w.obs_hour
    ORDER BY d.window_start DESC
    """

    df = con.execute(query).fetchdf()
    con.close()
    return df

def saved_features(df, output_dir="project/data/features/jz_combined"):
    os.makedirs(output_dir, exist_ok=True)
    path = f"{output_dir}/jz_features.parquet"
    df.to_parquet(path, index=False)
    print(f"Saved: {path}")
    return path

def main():
    print(f"Building features at {datetime.now(timezone.utc).isoformat()}")
    df = build_features()
    if df.empty:
        print("No feature data produced - check that processed parquet files exist")
        return
    
    print(f"Feature rows: {len(df)}")
    print(df[["route_id", "window_start", "avg_delay_sec", "alerts_active", "temperature_c", "is_extreme_heat"]].head(10))
    path = saved_features(df)
    print(f"Done: {path}")

if __name__ == "__main__":
    main()

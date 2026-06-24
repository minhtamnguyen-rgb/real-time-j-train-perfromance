from prefect import flow, task
import subprocess
import sys
from datetime import datetime, timezone

@task(retries=2, retry_delay_seconds=10)
def run_script(path: str):
    print(f"[{datetime.now(timezone.utc).isoformat()}] Running {path}")
    result = subprocess.run([sys.executable, path], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"{path} failed with code {result.returncode}")
    print(f"OK: {path}")

@task(retries=2, retry_delay_seconds=10)
def run_ingestion():
    scripts = [
        "project/ingestion/mta/trip_update.py",
        "project/ingestion/mta/alert.py",
        "project/ingestion/mta/vehicle_positions.py",
        "project/ingestion/weather/open_meteo.py",
    ]
    for s in scripts:
        run_script.fn(s)

@task(retries=2, retry_delay_seconds=10)
def run_processing():
    scripts = [
        "project/processing/clean_delays.py",
        "project/processing/clean_alerts.py",
        "project/processing/clean_weather.py",
        "project/processing/clean_vehicle_positions.py",
    ]
    for s in scripts:
        run_script.fn(s)

@task(retries=2, retry_delay_seconds=10)
def run_feature_join():
    run_script.fn("project/features/jz_weather_correlation.py")

@flow(name="jz-pipeline")
def jz_pipeline():
    run_ingestion()
    run_processing()
    run_feature_join()

if __name__ == "__main__":
    jz_pipeline.serve(
        name="jz-pipeline-every-15-min",
        interval=900,   # seconds = 15 minutes
    )
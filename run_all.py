import subprocess
import sys
from datetime import datetime, timezone

SCRIPTS = [
    "project/ingestion/mta/trip_update.py",
    "project/ingestion/mta/alert.py",
    "project/ingestion/mta/vehicle_positions.py",
    "project/ingestion/weather/open_meteo.py",
]

def run_script(path):
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Running {path}")
    result = subprocess.run([sys.executable, path], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(f"ERROR in {path}:\n{result.stderr}")
    else:
        print(f"OK: {path}")
    return result.returncode

def run_dbt():
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Running dbt")
    result = subprocess.run(
        [
            "/app/warehouse/.venv/bin/dbt",
            "run",
            "--project-dir", "/app/warehouse/jz_warehouse",
            "--profiles-dir", "/app/warehouse",
        ],
        capture_output=True,
        text=True,
        cwd="/app/warehouse/jz_warehouse"
    )
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(f"ERROR in dbt:\n{result.stderr}")
    else:
        print("OK: dbt run")
    return result.returncode

def main():
    print(f"Pipeline started at {datetime.now(timezone.utc).isoformat()}")
    errors = []
    for script in SCRIPTS:
        code = run_script(script)
        if code != 0:
            errors.append(script)

    print(f"\nIngestion finished. {len(SCRIPTS) - len(errors)}/{len(SCRIPTS)} succeeded.")

    dbt_code = run_dbt()
    if dbt_code != 0:
        errors.append("dbt")

    print(f"\nPipeline finished. Errors: {errors if errors else 'none'}")

if __name__ == "__main__":
    main()
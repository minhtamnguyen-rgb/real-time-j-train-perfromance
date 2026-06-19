import subprocess
import sys
from datetime import datetime, timezone

SCRIPTS = [
    "project/processing/clean_delays.py",
    "project/processing/clean_alerts.py",
    "project/processing/clean_weather.py",
    "project/processing/clean_vehicle_positions.py"
]

def run_script(path):
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Running {path} ")
    result = subprocess.run([sys.executable, path], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(f"ERROR in {path}:\n{result.stderr}")
    else:
        print(f"OK: {path}")
    return result.returncode

def main():
    print(f"Processing started at {datetime.now(timezone.utc).isoformat()}")
    errors = []
    for script in SCRIPTS:
        code = run_script(script)
        if code != 0:
            errors.append(script)
    
    print(f"\nProcessing finished. {len(SCRIPTS) - len(errors)}/{len(SCRIPTS)} scripts succeeded.")
    if errors:
        print(f"Failed scripts: {errors}")
        
if __name__ == "__main__":
    main()
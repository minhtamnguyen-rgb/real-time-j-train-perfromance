FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install pipeline dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install dbt in its own venv
COPY warehouse/requirements-dbt.txt ./warehouse/
RUN python3 -m venv warehouse/.venv && \
    warehouse/.venv/bin/pip install --no-cache-dir dbt-core dbt-duckdb

# Copy project code
COPY project/ ./project/
COPY run_all.py .
COPY run_processing.py .
COPY warehouse/jz_warehouse/ ./warehouse/jz_warehouse/

# Create dbt profiles directory
RUN mkdir -p /root/.dbt

# Write profiles.yml using environment variables
RUN cat > /root/.dbt/profiles.yml << 'EOF'
jz_warehouse:
  outputs:
    dev:
      type: duckdb
      path: /app/warehouse/dev.duckdb
      threads: 4
      settings:
        s3_access_key_id: "{{ env_var('R2_ACCESS_KEY_ID') }}"
        s3_secret_access_key: "{{ env_var('R2_SECRET_ACCESS_KEY') }}"
        s3_endpoint: "{{ env_var('R2_ENDPOINT_HOSTNAME') }}"
        s3_url_style: path
  target: dev
EOF

# Create data directories
RUN mkdir -p project/data/raw/mta/trip_updates \
             project/data/raw/mta/alerts \
             project/data/raw/mta/vehicle_positions \
             project/data/raw/weather \
             project/data/processed/delays \
             project/data/processed/alerts \
             project/data/processed/weather \
             project/data/processed/vehicle_positions \
             project/data/features/jz_combined

CMD ["python", "run_all.py"]
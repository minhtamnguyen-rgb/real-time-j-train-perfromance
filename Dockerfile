FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY project/ ./project/
COPY run_all.py .

# Create data directories
RUN mkdir -p project/data/raw/mta/trip_updates \
             project/data/raw/mta/alerts \
             project/data/raw/mta/vehicle_positions \
             project/data/raw/weather

CMD ["python", "run_all.py"]
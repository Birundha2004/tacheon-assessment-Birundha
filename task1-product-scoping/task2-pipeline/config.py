# config.py — All pipeline parameters in one place. No hardcoded values in logic.

# --- API Settings ---
LATITUDE = 13.0827          # Chennai, India
LONGITUDE = 80.2707
LOCATION_NAME = "Chennai"
FORECAST_DAYS = 7           # How many days of data to fetch

API_BASE_URL = "https://api.open-meteo.com/v1/forecast"

API_PARAMS = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "daily": [
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_sum",
        "windspeed_10m_max",
        "weathercode",
    ],
    "timezone": "Asia/Kolkata",
    "forecast_days": FORECAST_DAYS,
}

# --- BigQuery Settings ---
GCP_PROJECT_ID = "utopian-domain-426110-j3"   # Your project ID
BQ_DATASET = "weather_pipeline"
BQ_TABLE = "daily_weather"

# --- Pipeline Settings ---
PIPELINE_VERSION = "1.0"

"""
pipeline.py — Weather Data Pipeline
Fetches daily weather data from Open-Meteo, transforms it, and loads it into BigQuery.

Usage:
    python pipeline.py

Author: Birundha
"""

import logging
import sys
from datetime import datetime, timezone

import pandas as pd
import requests
from google.cloud import bigquery
from google.api_core.exceptions import NotFound

import config

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step 1: Fetch
# ---------------------------------------------------------------------------
def fetch_weather() -> dict:
    """Call Open-Meteo API and return raw JSON response."""
    log.info("Fetching weather data for %s (lat=%s, lon=%s)",
             config.LOCATION_NAME, config.LATITUDE, config.LONGITUDE)

    try:
        response = requests.get(
            config.API_BASE_URL,
            params=config.API_PARAMS,
            timeout=15,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        log.error("Could not connect to Open-Meteo API. Check your internet connection.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        log.error("Request to Open-Meteo API timed out after 15 seconds.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        log.error("API returned an error: %s", e)
        sys.exit(1)

    data = response.json()

    # Validate the response has what we expect
    if "daily" not in data:
        log.error("Unexpected API response structure — 'daily' key missing. Got: %s", list(data.keys()))
        sys.exit(1)

    log.info("Successfully fetched %d days of weather data.", config.FORECAST_DAYS)
    return data


# ---------------------------------------------------------------------------
# Step 2: Transform
# ---------------------------------------------------------------------------

# WMO weather code descriptions (subset)
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def transform_weather(raw: dict) -> pd.DataFrame:
    """Flatten raw API response into a clean tabular DataFrame with derived fields."""
    log.info("Transforming raw data...")

    daily = raw["daily"]

    df = pd.DataFrame({
        "date":             daily.get("time", []),
        "temp_max_c":       daily.get("temperature_2m_max", []),
        "temp_min_c":       daily.get("temperature_2m_min", []),
        "precipitation_mm": daily.get("precipitation_sum", []),
        "windspeed_max_kmh":daily.get("windspeed_10m_max", []),
        "weather_code":     daily.get("weathercode", []),
    })

    # --- Handle nulls ---
    before = len(df)
    df = df.dropna(subset=["date", "temp_max_c", "temp_min_c"])
    dropped = before - len(df)
    if dropped:
        log.warning("Dropped %d rows with missing required fields.", dropped)

    df["precipitation_mm"] = df["precipitation_mm"].fillna(0.0)
    df["windspeed_max_kmh"] = df["windspeed_max_kmh"].fillna(0.0)
    df["weather_code"] = df["weather_code"].fillna(0).astype(int)

    # --- Type coercions ---
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["temp_max_c"] = df["temp_max_c"].astype(float).round(1)
    df["temp_min_c"] = df["temp_min_c"].astype(float).round(1)
    df["precipitation_mm"] = df["precipitation_mm"].astype(float).round(2)
    df["windspeed_max_kmh"] = df["windspeed_max_kmh"].astype(float).round(1)

    # --- Derived fields (analytical value beyond raw API data) ---

    # 1. Daily temperature range — useful for detecting extreme weather days
    df["temp_range_c"] = (df["temp_max_c"] - df["temp_min_c"]).round(1)

    # 2. Average temperature — simple midpoint estimate
    df["temp_avg_c"] = ((df["temp_max_c"] + df["temp_min_c"]) / 2).round(1)

    # 3. Human-readable weather description from WMO code
    df["weather_description"] = df["weather_code"].map(WMO_CODES).fillna("Unknown")

    # 4. Rain day flag — boolean, useful for aggregation queries
    df["is_rain_day"] = df["precipitation_mm"] > 0.0

    # 5. Location metadata
    df["location"] = config.LOCATION_NAME
    df["latitude"] = config.LATITUDE
    df["longitude"] = config.LONGITUDE

    # 6. Pipeline metadata — when this row was loaded
    df["loaded_at"] = datetime.now(timezone.utc).isoformat()

    log.info("Transformation complete. %d rows ready to load.", len(df))
    return df


# ---------------------------------------------------------------------------
# Step 3: Load to BigQuery
# ---------------------------------------------------------------------------

SCHEMA = [
    bigquery.SchemaField("date",               "DATE",    mode="REQUIRED"),
    bigquery.SchemaField("location",           "STRING",  mode="REQUIRED"),
    bigquery.SchemaField("latitude",           "FLOAT",   mode="NULLABLE"),
    bigquery.SchemaField("longitude",          "FLOAT",   mode="NULLABLE"),
    bigquery.SchemaField("temp_max_c",         "FLOAT",   mode="NULLABLE"),
    bigquery.SchemaField("temp_min_c",         "FLOAT",   mode="NULLABLE"),
    bigquery.SchemaField("temp_avg_c",         "FLOAT",   mode="NULLABLE"),
    bigquery.SchemaField("temp_range_c",       "FLOAT",   mode="NULLABLE"),
    bigquery.SchemaField("precipitation_mm",   "FLOAT",   mode="NULLABLE"),
    bigquery.SchemaField("windspeed_max_kmh",  "FLOAT",   mode="NULLABLE"),
    bigquery.SchemaField("weather_code",       "INTEGER", mode="NULLABLE"),
    bigquery.SchemaField("weather_description","STRING",  mode="NULLABLE"),
    bigquery.SchemaField("is_rain_day",        "BOOLEAN", mode="NULLABLE"),
    bigquery.SchemaField("loaded_at",          "STRING",  mode="NULLABLE"),
]


def ensure_dataset(client: bigquery.Client) -> None:
    """Create the dataset if it doesn't already exist."""
    dataset_ref = f"{config.GCP_PROJECT_ID}.{config.BQ_DATASET}"
    try:
        client.get_dataset(dataset_ref)
        log.info("Dataset '%s' already exists.", config.BQ_DATASET)
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset)
        log.info("Created dataset '%s'.", config.BQ_DATASET)


def load_to_bigquery(df: pd.DataFrame) -> None:
    """Load transformed DataFrame into BigQuery, replacing today's data."""
    log.info("Connecting to BigQuery project '%s'...", config.GCP_PROJECT_ID)

    try:
        client = bigquery.Client(project=config.GCP_PROJECT_ID)
    except Exception as e:
        log.error("Failed to initialise BigQuery client: %s", e)
        log.error("Make sure you have run: gcloud auth application-default login")
        sys.exit(1)

    ensure_dataset(client)

    table_ref = f"{config.GCP_PROJECT_ID}.{config.BQ_DATASET}.{config.BQ_TABLE}"

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Replace on each run
        source_format=bigquery.SourceFormat.CSV,
    )

    log.info("Loading %d rows into %s...", len(df), table_ref)

    try:
        job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()  # Wait for the job to complete
    except Exception as e:
        log.error("BigQuery load failed: %s", e)
        sys.exit(1)

    table = client.get_table(table_ref)
    log.info("Load complete. Table now has %d rows.", table.num_rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_pipeline() -> None:
    log.info("=== Weather Pipeline v%s starting ===", config.PIPELINE_VERSION)
    raw = fetch_weather()
    df = transform_weather(raw)
    load_to_bigquery(df)
    log.info("=== Pipeline finished successfully ===")


if __name__ == "__main__":
    run_pipeline()

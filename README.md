# tacheon-assessment-Birundha
# Tacheon Assessment – Data & AI Product Engineer

Assessment tasks submitted for the Data & AI Product Engineer role at Tacheon/Smacient.

## Repository Structure

- `/task1-product-scoping` – Product brief and scoping document
- `/task2-pipeline` – Python data pipeline + BigQuery + SQL

## Status
- [ ] Task 1: Product Scoping
- [ ] Task 2: Pipeline Building

*Work in progress – started Day 1*
Task 1: Add product brief and v1 scope
Task ! completed
# Task 2: Data Pipeline — Weather Data → BigQuery

## What This Does

This pipeline fetches 7-day weather forecast data for Chennai from the [Open-Meteo API](https://open-meteo.com/), transforms it into a clean tabular format with derived analytical fields, and loads it into Google BigQuery.

---

## Why Open-Meteo?

- Completely free, no API key required — zero setup friction
- Returns rich structured data (temperatures, precipitation, wind, weather codes)
- Reliable uptime and well-documented
- Allows meaningful derived fields (temperature range, rain day flags, WMO descriptions)
- Universally understood data — easy to verify correctness at a glance

---

## Pipeline Architecture

```
Open-Meteo API (free, no key)
        ↓
  fetch_weather()
  — HTTP GET with parameterised config
  — Error handling: timeouts, HTTP errors, unexpected structure
        ↓
  transform_weather()
  — Flatten JSON → pandas DataFrame
  — Handle nulls and type mismatches
  — Add derived fields (see below)
        ↓
  load_to_bigquery()
  — Auto-create dataset if missing
  — WRITE_TRUNCATE: replace data on each run
  — Explicit schema with correct data types
        ↓
  BigQuery: utopian-domain-426110-j3.weather_pipeline.daily_weather
```

---

## Derived Fields Added

These go beyond what the API returns raw and add analytical value:

| Field | Description |
|---|---|
| `temp_avg_c` | Average of max and min temperature — useful midpoint estimate |
| `temp_range_c` | Max minus min — detects extreme temperature swing days |
| `weather_description` | Human-readable label mapped from WMO weather code |
| `is_rain_day` | Boolean flag — TRUE if any precipitation recorded |
| `loaded_at` | UTC timestamp of when this row was loaded — supports auditability |

---

## How to Run

### 1. Clone the repo and navigate to the pipeline folder

```bash
git clone https://github.com/Birundha2004/tacheon-assessment-Birundha.git
cd tacheon-assessment-Birundha/task2-pipeline
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

This opens a browser window. Sign in with the same Google account you used for BigQuery.

If you don't have the gcloud CLI installed:
→ https://cloud.google.com/sdk/docs/install

### 4. Run the pipeline

```bash
python pipeline.py
```

You should see logs like:
```
2026-05-29 14:02:12  INFO     === Weather Pipeline v1.0 starting ===
2026-05-29 14:02:12  INFO     Fetching weather data for Chennai (lat=13.0827, lon=80.2707)
2026-05-29 14:02:13  INFO     Successfully fetched 7 days of weather data.
2026-05-29 14:02:13  INFO     Transforming raw data...
2026-05-29 14:02:13  INFO     Transformation complete. 7 rows ready to load.
2026-05-29 14:02:13  INFO     Connecting to BigQuery project 'utopian-domain-426110-j3'...
2026-05-29 14:02:18  INFO     Created dataset 'weather_pipeline'.
2026-05-29 14:02:18  INFO     Loading 7 rows into utopian-domain-426110-j3.weather_pipeline.daily_weather...
2026-05-29 14:02:26  INFO     Load complete. Table now has 7 rows.
2026-05-29 14:02:26  INFO     === Pipeline finished successfully ===
```

---

## BigQuery Setup

- **Project ID:** `utopian-domain-426110-j3`
- **Dataset:** `weather_pipeline`
- **Table:** `daily_weather`

The pipeline auto-creates the dataset and table on first run. No manual setup needed in BigQuery console.

The BigQuery Sandbox (free tier) was used — no billing account required. Key sandbox limitations understood and worked within:
- No streaming inserts (used batch load instead — `load_table_from_dataframe`)
- Tables expire after 60 days (acceptable for this use case)
- 10GB free storage and 1TB free queries per month

---

## SQL Summary Query

File: `queries/summary.sql`

```sql
SELECT
  location,
  MIN(date)                        AS week_start,
  MAX(date)                        AS week_end,
  ROUND(AVG(temp_avg_c), 1)        AS avg_temp_c,
  ROUND(MAX(temp_max_c), 1)        AS hottest_day_c,
  ROUND(MIN(temp_min_c), 1)        AS coldest_night_c,
  ROUND(SUM(precipitation_mm), 2)  AS total_rainfall_mm,
  COUNTIF(is_rain_day = TRUE)       AS rain_days,
  ROUND(MAX(windspeed_max_kmh), 1) AS peak_wind_kmh

FROM `utopian-domain-426110-j3.weather_pipeline.daily_weather`
GROUP BY location
ORDER BY location;
```

### Sample Output

| location | week_start | week_end | avg_temp_c | hottest_day_c | coldest_night_c | total_rainfall_mm | rain_days | peak_wind_kmh |
|---|---|---|---|---|---|---|---|---|
| Chennai | 2026-05-29 | 2026-06-04 | 33.2 | 39.0 | 27.2 | 6.0 | 6 | 17.3 |

---

## Production Thinking (Step 5)

### How would you schedule this pipeline to run automatically?

I would use **Google Cloud Scheduler** + **Cloud Run** (or a Cloud Function):
- Cloud Scheduler triggers the job every morning at 7am IST via a HTTP POST
- The pipeline runs in a containerised Cloud Run job
- This keeps it serverless — no infrastructure to manage, and it scales to zero when not running

For a simpler setup, a cron job on a VM or a GitHub Actions scheduled workflow would also work:
```
0 7 * * * cd /path/to/pipeline && python pipeline.py
```

### How would you know if it failed?

- The pipeline already logs every step with timestamps. In production, these logs would go to **Google Cloud Logging** automatically when running on GCP.
- I would set up a **Cloud Monitoring alert** that fires if the pipeline job fails or if no new rows are written to BigQuery within a time window.
- For immediate notification, a Slack webhook or email alert on job failure.
- The table's `loaded_at` field also acts as a lightweight freshness check — a simple SQL query can verify data was loaded today.

### What would you add or change if this needed to scale to 10x the data volume?

- Switch from `WRITE_TRUNCATE` to **incremental loads** with `WRITE_APPEND` and deduplication logic — avoids reloading all data on every run
- Add **partitioning by date** on the BigQuery table — queries become faster and cheaper at scale
- Move transformation to **Apache Beam / Dataflow** if the data volume justifies distributed processing
- Add a **data quality check layer** (e.g. Great Expectations) before loading — validate row counts, value ranges, and null rates
- Store raw API responses in **Cloud Storage** before transformation — gives a reprocessing safety net if the schema changes

---

## What I Would Do Differently With More Time

- Add unit tests for the transformation logic — especially the derived field calculations and null handling
- Parameterise the location so multiple cities can be run in one pipeline execution
- Add incremental loading (only fetch and load new dates, not replace everything each run)
- Build a simple dashboard on top of the BigQuery table using Looker Studio
- Add a `pipeline_runs` audit table that logs each execution with row count, duration, and status

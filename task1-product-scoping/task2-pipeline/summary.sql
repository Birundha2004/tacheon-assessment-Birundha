-- summary.sql
-- Extracts a meaningful weekly weather summary from the daily_weather table.
-- Shows average temperature, total rainfall, hottest day, and rain day count.

SELECT
  location,
  MIN(date)                                        AS week_start,
  MAX(date)                                        AS week_end,
  ROUND(AVG(temp_avg_c), 1)                        AS avg_temp_c,
  ROUND(MAX(temp_max_c), 1)                        AS hottest_day_c,
  ROUND(MIN(temp_min_c), 1)                        AS coldest_night_c,
  ROUND(SUM(precipitation_mm), 2)                  AS total_rainfall_mm,
  COUNTIF(is_rain_day = TRUE)                      AS rain_days,
  ROUND(MAX(windspeed_max_kmh), 1)                 AS peak_wind_kmh,
  MAX(IF(temp_max_c = MAX(temp_max_c) OVER (), date, NULL))  AS hottest_date

FROM `utopian-domain-426110-j3.weather_pipeline.daily_weather`

GROUP BY location
ORDER BY location;

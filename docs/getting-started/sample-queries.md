# Sample Queries

Explore BigQuery-Lite's capabilities with these sample queries using the included NYC taxi dataset. These examples demonstrate various SQL features and help you understand the differences between DuckDB and ClickHouse engines.

## Dataset Overview

The NYC taxi dataset contains 50,000 taxi trip records with the following schema:

```sql
-- View the table structure
DESCRIBE nyc_taxi;
```

**Key Columns:**
- `tpep_pickup_datetime` - Trip start timestamp
- `tpep_dropoff_datetime` - Trip end timestamp  
- `fare_amount` - Base fare amount
- `total_amount` - Total amount charged
- `payment_type` - Payment method (1=Credit, 2=Cash, etc.)
- `trip_distance` - Distance in miles
- `passenger_count` - Number of passengers
- `pickup_location_id` - Pickup location zone
- `dropoff_location_id` - Dropoff location zone

## Basic Exploration Queries

### 1. Dataset Overview

Get basic statistics about the dataset:

```sql
-- Dataset size and basic stats
SELECT 
    COUNT(*) as total_trips,
    MIN(tpep_pickup_datetime) as earliest_trip,
    MAX(tpep_pickup_datetime) as latest_trip,
    AVG(fare_amount) as avg_fare,
    AVG(trip_distance) as avg_distance,
    AVG(total_amount) as avg_total
FROM nyc_taxi;
```

**Expected Results:**
- Total trips: 50,000
- Date range: Subset of NYC taxi data
- Average fare: ~$13
- Average distance: ~3 miles

### 2. Data Quality Check

Check for data quality issues:

```sql
-- Data quality assessment
SELECT 
    'Total Records' as metric,
    COUNT(*) as value
FROM nyc_taxi

UNION ALL

SELECT 
    'Records with Zero Fare',
    COUNT(*)
FROM nyc_taxi 
WHERE fare_amount <= 0

UNION ALL

SELECT 
    'Records with Zero Distance',
    COUNT(*)
FROM nyc_taxi 
WHERE trip_distance <= 0

UNION ALL

SELECT 
    'Records with Negative Duration',
    COUNT(*)
FROM nyc_taxi 
WHERE tpep_dropoff_datetime <= tpep_pickup_datetime;
```

## Aggregation and Grouping

### 3. Payment Type Analysis

Analyze payment patterns:

```sql
-- Payment method distribution
SELECT 
    CASE 
        WHEN payment_type = 1 THEN 'Credit Card'
        WHEN payment_type = 2 THEN 'Cash'
        WHEN payment_type = 3 THEN 'No Charge'
        WHEN payment_type = 4 THEN 'Dispute'
        WHEN payment_type = 5 THEN 'Unknown'
        ELSE 'Other'
    END as payment_method,
    COUNT(*) as trip_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
    ROUND(AVG(fare_amount), 2) as avg_fare,
    ROUND(AVG(total_amount), 2) as avg_total,
    ROUND(SUM(total_amount), 2) as total_revenue
FROM nyc_taxi 
WHERE fare_amount > 0  -- Exclude invalid fares
GROUP BY payment_type 
ORDER BY trip_count DESC;
```

### 4. Trip Distance Distribution

Analyze trip distances:

```sql
-- Trip distance buckets
SELECT 
    CASE 
        WHEN trip_distance = 0 THEN '0 miles'
        WHEN trip_distance <= 1 THEN '0-1 miles'
        WHEN trip_distance <= 3 THEN '1-3 miles'
        WHEN trip_distance <= 5 THEN '3-5 miles'
        WHEN trip_distance <= 10 THEN '5-10 miles'
        WHEN trip_distance <= 20 THEN '10-20 miles'
        ELSE '20+ miles'
    END as distance_bucket,
    COUNT(*) as trips,
    ROUND(AVG(fare_amount), 2) as avg_fare,
    ROUND(AVG(total_amount), 2) as avg_total,
    ROUND(AVG(trip_distance), 2) as avg_distance
FROM nyc_taxi
GROUP BY 
    CASE 
        WHEN trip_distance = 0 THEN '0 miles'
        WHEN trip_distance <= 1 THEN '0-1 miles'
        WHEN trip_distance <= 3 THEN '1-3 miles'
        WHEN trip_distance <= 5 THEN '3-5 miles'
        WHEN trip_distance <= 10 THEN '5-10 miles'
        WHEN trip_distance <= 20 THEN '10-20 miles'
        ELSE '20+ miles'
    END
ORDER BY 
    MIN(trip_distance);
```

## Time Series Analysis

### 5. Hourly Trip Patterns

Analyze trips by hour of day:

```sql
-- Trips by hour of day
SELECT 
    EXTRACT(hour FROM tpep_pickup_datetime) as pickup_hour,
    COUNT(*) as trips,
    ROUND(AVG(fare_amount), 2) as avg_fare,
    ROUND(AVG(trip_distance), 2) as avg_distance,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM nyc_taxi 
GROUP BY EXTRACT(hour FROM tpep_pickup_datetime)
ORDER BY pickup_hour;
```

### 6. Daily Trip Trends

Analyze daily patterns:

```sql
-- Daily trip patterns
SELECT 
    DATE(tpep_pickup_datetime) as trip_date,
    EXTRACT(dow FROM tpep_pickup_datetime) as day_of_week,
    CASE EXTRACT(dow FROM tpep_pickup_datetime)
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as day_name,
    COUNT(*) as daily_trips,
    ROUND(AVG(fare_amount), 2) as avg_fare,
    ROUND(SUM(total_amount), 2) as daily_revenue
FROM nyc_taxi 
GROUP BY 
    DATE(tpep_pickup_datetime),
    EXTRACT(dow FROM tpep_pickup_datetime)
ORDER BY trip_date;
```

## Advanced Analytics

### 7. Moving Averages

Calculate rolling averages for trend analysis:

```sql
-- 7-day moving average of daily trips
WITH daily_stats AS (
    SELECT 
        DATE(tpep_pickup_datetime) as trip_date,
        COUNT(*) as daily_trips,
        AVG(fare_amount) as avg_daily_fare,
        SUM(total_amount) as daily_revenue
    FROM nyc_taxi 
    GROUP BY DATE(tpep_pickup_datetime)
)
SELECT 
    trip_date,
    daily_trips,
    ROUND(avg_daily_fare, 2) as avg_fare,
    ROUND(daily_revenue, 2) as revenue,
    ROUND(AVG(daily_trips) OVER (
        ORDER BY trip_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 1) as trips_7day_avg,
    ROUND(AVG(daily_revenue) OVER (
        ORDER BY trip_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) as revenue_7day_avg
FROM daily_stats
ORDER BY trip_date;
```

### 8. Percentile Analysis

Analyze fare distribution using percentiles:

```sql
-- Fare amount percentile analysis
SELECT 
    'Fare Amount Percentiles' as metric,
    ROUND(MIN(fare_amount), 2) as min_value,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY fare_amount), 2) as p25,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fare_amount), 2) as median,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY fare_amount), 2) as p75,
    ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY fare_amount), 2) as p90,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY fare_amount), 2) as p95,
    ROUND(MAX(fare_amount), 2) as max_value
FROM nyc_taxi 
WHERE fare_amount > 0

UNION ALL

SELECT 
    'Trip Distance Percentiles',
    ROUND(MIN(trip_distance), 2),
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY trip_distance), 2),
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY trip_distance), 2),
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY trip_distance), 2),
    ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY trip_distance), 2),
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY trip_distance), 2),
    ROUND(MAX(trip_distance), 2)
FROM nyc_taxi 
WHERE trip_distance > 0;
```

### 9. Correlation Analysis

Find correlations between variables:

```sql
-- Correlation between distance and fare
WITH fare_distance AS (
    SELECT 
        trip_distance,
        fare_amount,
        total_amount,
        EXTRACT(epoch FROM (tpep_dropoff_datetime - tpep_pickup_datetime))/60 as duration_minutes
    FROM nyc_taxi 
    WHERE fare_amount > 0 
      AND trip_distance > 0
      AND tpep_dropoff_datetime > tpep_pickup_datetime
)
SELECT 
    COUNT(*) as valid_trips,
    ROUND(CORR(trip_distance, fare_amount), 3) as distance_fare_correlation,
    ROUND(CORR(duration_minutes, fare_amount), 3) as duration_fare_correlation,
    ROUND(CORR(trip_distance, duration_minutes), 3) as distance_duration_correlation,
    ROUND(AVG(fare_amount / NULLIF(trip_distance, 0)), 2) as avg_fare_per_mile
FROM fare_distance;
```

## Engine Comparison Queries

### 10. Performance Comparison

Compare DuckDB vs ClickHouse performance with the same query:

```sql
-- Large aggregation query (test on both engines)
SELECT 
    DATE(tpep_pickup_datetime) as trip_date,
    EXTRACT(hour FROM tpep_pickup_datetime) as trip_hour,
    COUNT(*) as trips,
    COUNT(DISTINCT pickup_location_id) as unique_pickup_zones,
    COUNT(DISTINCT dropoff_location_id) as unique_dropoff_zones,
    ROUND(AVG(fare_amount), 2) as avg_fare,
    ROUND(AVG(trip_distance), 2) as avg_distance,
    ROUND(AVG(EXTRACT(epoch FROM (tpep_dropoff_datetime - tpep_pickup_datetime))/60), 1) as avg_duration_minutes,
    ROUND(SUM(total_amount), 2) as total_revenue,
    ROUND(STDDEV(fare_amount), 2) as fare_stddev
FROM nyc_taxi 
WHERE fare_amount > 0 
  AND trip_distance > 0
  AND tpep_dropoff_datetime > tpep_pickup_datetime
GROUP BY 
    DATE(tpep_pickup_datetime),
    EXTRACT(hour FROM tpep_pickup_datetime)
ORDER BY trip_date, trip_hour;
```

### 11. Complex Window Functions

Test advanced SQL features:

```sql
-- Ranking and window functions
WITH trip_rankings AS (
    SELECT 
        tpep_pickup_datetime,
        fare_amount,
        trip_distance,
        total_amount,
        ROW_NUMBER() OVER (ORDER BY fare_amount DESC) as fare_rank,
        ROW_NUMBER() OVER (ORDER BY trip_distance DESC) as distance_rank,
        NTILE(10) OVER (ORDER BY fare_amount) as fare_decile,
        LAG(fare_amount, 1) OVER (ORDER BY tpep_pickup_datetime) as prev_fare,
        LEAD(fare_amount, 1) OVER (ORDER BY tpep_pickup_datetime) as next_fare
    FROM nyc_taxi 
    WHERE fare_amount > 0 AND trip_distance > 0
)
SELECT 
    fare_decile,
    COUNT(*) as trips_in_decile,
    ROUND(MIN(fare_amount), 2) as min_fare,
    ROUND(MAX(fare_amount), 2) as max_fare,
    ROUND(AVG(fare_amount), 2) as avg_fare,
    ROUND(AVG(trip_distance), 2) as avg_distance
FROM trip_rankings
GROUP BY fare_decile
ORDER BY fare_decile;
```

## Data Export Queries

### 12. Summary Report

Generate a comprehensive summary report:

```sql
-- Executive summary report
WITH base_stats AS (
    SELECT 
        COUNT(*) as total_trips,
        COUNT(DISTINCT DATE(tpep_pickup_datetime)) as days_of_data,
        SUM(total_amount) as total_revenue,
        AVG(fare_amount) as avg_fare,
        AVG(trip_distance) as avg_distance,
        AVG(EXTRACT(epoch FROM (tpep_dropoff_datetime - tpep_pickup_datetime))/60) as avg_duration
    FROM nyc_taxi 
    WHERE fare_amount > 0 AND trip_distance > 0
),
payment_stats AS (
    SELECT 
        payment_type,
        COUNT(*) as trips,
        SUM(total_amount) as revenue
    FROM nyc_taxi WHERE fare_amount > 0
    GROUP BY payment_type
)
SELECT 
    'NYC Taxi Dataset Summary' as report_title,
    b.total_trips,
    b.days_of_data,
    ROUND(b.total_revenue, 2) as total_revenue,
    ROUND(b.total_revenue / b.days_of_data, 2) as avg_daily_revenue,
    ROUND(b.avg_fare, 2) as avg_fare,
    ROUND(b.avg_distance, 2) as avg_distance_miles,
    ROUND(b.avg_duration, 1) as avg_duration_minutes,
    (SELECT COUNT(*) FROM payment_stats WHERE payment_type = 1) as credit_card_trips,
    (SELECT COUNT(*) FROM payment_stats WHERE payment_type = 2) as cash_trips,
    ROUND((SELECT revenue FROM payment_stats WHERE payment_type = 1), 2) as credit_card_revenue,
    ROUND((SELECT revenue FROM payment_stats WHERE payment_type = 2), 2) as cash_revenue
FROM base_stats b;
```

## Tips for Using These Queries

### DuckDB Specific Features
- Excellent for exploratory analysis
- Fast aggregations on medium datasets
- Rich SQL feature set including window functions
- Great for development and testing

### ClickHouse Specific Features  
- Better for large dataset analysis
- Optimized for columnar operations
- Excellent compression and storage efficiency
- Ideal for production analytics

### Performance Tips
1. **Use LIMIT** during development to avoid large result sets
2. **Add WHERE clauses** to filter data early
3. **Use appropriate engines** based on data size and complexity
4. **Monitor execution time** in the web interface
5. **Compare results** between engines to verify consistency

### Query Modification Ideas
- Change date ranges to focus on specific time periods
- Add geographic analysis using pickup/dropoff location IDs
- Create cohort analysis based on trip patterns
- Build customer segmentation based on trip behavior
- Analyze seasonal patterns in the data

## Next Steps

- **[Web Interface Guide](../user-guide/web-interface.md)** - Learn to use the query interface effectively
- **[Query Writing](../user-guide/query-writing.md)** - SQL best practices and syntax
- **[Data Management](../user-guide/data-management.md)** - Load your own datasets
- **[Performance Optimization](../advanced/performance.md)** - Optimize query performance
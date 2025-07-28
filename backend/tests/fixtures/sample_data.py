"""
Test fixtures and sample data for runner tests

Provides common test data, mock responses, and utility functions
for testing DuckDB and ClickHouse runners.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import random


class SampleDataGenerator:
    """Generator for sample test data"""
    
    @staticmethod
    def generate_nyc_taxi_data(count: int = 100) -> List[Dict[str, Any]]:
        """Generate sample NYC taxi trip data"""
        payment_types = ["cash", "credit_card", "dispute", "no_charge"]
        base_time = datetime(2023, 1, 1)
        
        data = []
        for i in range(count):
            pickup_time = base_time + timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            trip_duration = timedelta(minutes=random.randint(5, 120))
            dropoff_time = pickup_time + trip_duration
            
            fare_amount = round(random.uniform(5.0, 50.0), 2)
            tip_amount = round(random.uniform(0.0, fare_amount * 0.3), 2)
            total_amount = round(fare_amount + tip_amount + random.uniform(0.5, 3.0), 2)
            
            data.append({
                "id": i + 1,
                "payment_type": random.choice(payment_types),
                "fare_amount": fare_amount,
                "trip_distance": round(random.uniform(0.5, 15.0), 2),
                "total_amount": total_amount,
                "passenger_count": random.randint(1, 6),
                "tpep_pickup_datetime": pickup_time,
                "tpep_dropoff_datetime": dropoff_time,
                "tip_amount": tip_amount
            })
        
        return data

    @staticmethod
    def generate_user_events(count: int = 50) -> List[Dict[str, Any]]:
        """Generate sample user event data"""
        event_types = ["click", "view", "purchase", "signup", "logout"]
        devices = ["desktop", "mobile", "tablet"]
        browsers = ["chrome", "firefox", "safari", "edge"]
        locations = ["US", "CA", "UK", "DE", "FR", "JP", "AU"]
        
        data = []
        base_time = datetime(2023, 1, 1)
        
        for i in range(count):
            event_time = base_time + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            
            data.append({
                "user_id": f"user_{random.randint(1, 1000)}",
                "event_type": random.choice(event_types),
                "timestamp": int(event_time.timestamp()),
                "page_url": f"/page_{random.randint(1, 50)}",
                "session_id": f"session_{random.randint(1, 200)}",
                "metadata": {
                    "device_type": random.choice(devices),
                    "browser": random.choice(browsers),
                    "location": random.choice(locations),
                    "is_premium": random.choice([True, False])
                }
            })
        
        return data

    @staticmethod
    def generate_sample_metrics() -> Dict[str, Any]:
        """Generate sample performance metrics"""
        return {
            "execution_time": round(random.uniform(0.01, 2.0), 3),
            "memory_used_mb": round(random.uniform(0.1, 100.0), 2),
            "rows_processed": random.randint(1, 10000),
            "cpu_time": round(random.uniform(0.005, 1.5), 3),
            "io_wait": round(random.uniform(0.001, 0.5), 3),
            "network_time": round(random.uniform(0.0, 0.2), 3)
        }


class MockResponses:
    """Mock responses for testing database interactions"""
    
    @staticmethod
    def clickhouse_table_info() -> List[tuple]:
        """Mock ClickHouse table information response"""
        return [
            ("nyc_taxi", "MergeTree"),
            ("sample_data", "MergeTree"),
            ("user_events", "MergeTree")
        ]
    
    @staticmethod
    def clickhouse_column_info() -> List[tuple]:
        """Mock ClickHouse column information response"""
        return [
            ("id", "UInt64"),
            ("payment_type", "String"),
            ("fare_amount", "Float64"),
            ("trip_distance", "Float64"),
            ("total_amount", "Float64"),
            ("passenger_count", "UInt8"),
            ("tpep_pickup_datetime", "DateTime"),
            ("tpep_dropoff_datetime", "DateTime"),
            ("tip_amount", "Float64")
        ]
    
    @staticmethod
    def duckdb_table_info() -> List[tuple]:
        """Mock DuckDB table information response"""
        return [
            ("nyc_taxi", "BASE TABLE"),
            ("sample_data", "BASE TABLE"),
            ("user_events", "BASE TABLE")
        ]
    
    @staticmethod
    def duckdb_column_info() -> List[tuple]:
        """Mock DuckDB column information response"""
        return [
            ("id", "INTEGER"),
            ("payment_type", "VARCHAR"),
            ("fare_amount", "DOUBLE"),
            ("trip_distance", "DOUBLE"),
            ("total_amount", "DOUBLE"),
            ("passenger_count", "INTEGER"),
            ("tpep_pickup_datetime", "TIMESTAMP"),
            ("tpep_dropoff_datetime", "TIMESTAMP"),
            ("tip_amount", "DOUBLE")
        ]
    
    @staticmethod
    def clickhouse_cluster_info() -> List[tuple]:
        """Mock ClickHouse cluster information response"""
        return [
            ("test_cluster", 1, 1, "localhost", 9000),
            ("test_cluster", 1, 2, "localhost", 9001),
            ("test_cluster", 2, 1, "localhost", 9002)
        ]
    
    @staticmethod
    def clickhouse_server_info() -> List[tuple]:
        """Mock ClickHouse server information response"""
        return [("23.8.1.1", "test-server", 86400)]  # version, hostname, uptime
    
    @staticmethod
    def query_explain_plan() -> List[str]:
        """Mock query execution plan"""
        return [
            "Seq Scan on nyc_taxi (cost=0.00..180.00 rows=10000 width=32)",
            "Filter: (fare_amount > 0::double precision)",
            "Planning time: 0.123 ms",
            "Execution time: 45.678 ms"
        ]


class TestQueries:
    """Collection of test SQL queries"""
    
    SIMPLE_QUERIES = [
        "SELECT 1",
        "SELECT 1 as test_value",
        "SELECT 'hello' as greeting",
        "SELECT NOW() as current_time"
    ]
    
    BASIC_SELECT_QUERIES = [
        "SELECT * FROM nyc_taxi LIMIT 10",
        "SELECT payment_type, fare_amount FROM nyc_taxi LIMIT 5",
        "SELECT COUNT(*) FROM sample_data",
        "SELECT AVG(fare_amount) as avg_fare FROM nyc_taxi"
    ]
    
    COMPLEX_QUERIES = [
        """
        SELECT 
            payment_type,
            COUNT(*) as trip_count,
            AVG(fare_amount) as avg_fare,
            MIN(fare_amount) as min_fare,
            MAX(fare_amount) as max_fare
        FROM nyc_taxi 
        WHERE fare_amount > 0 
        GROUP BY payment_type 
        ORDER BY avg_fare DESC
        """,
        """
        SELECT 
            DATE_TRUNC('day', tpep_pickup_datetime) as trip_date,
            payment_type,
            COUNT(*) as daily_trips,
            SUM(total_amount) as daily_revenue
        FROM nyc_taxi 
        GROUP BY DATE_TRUNC('day', tpep_pickup_datetime), payment_type
        ORDER BY trip_date, payment_type
        """,
        """
        WITH trip_stats AS (
            SELECT 
                payment_type,
                AVG(fare_amount) as avg_fare,
                STDDEV(fare_amount) as fare_stddev
            FROM nyc_taxi 
            GROUP BY payment_type
        )
        SELECT 
            t.*,
            ts.avg_fare,
            CASE 
                WHEN t.fare_amount > ts.avg_fare + ts.fare_stddev THEN 'high'
                WHEN t.fare_amount < ts.avg_fare - ts.fare_stddev THEN 'low'
                ELSE 'normal'
            END as fare_category
        FROM nyc_taxi t
        JOIN trip_stats ts ON t.payment_type = ts.payment_type
        LIMIT 100
        """
    ]
    
    WINDOW_FUNCTION_QUERIES = [
        """
        SELECT 
            id,
            fare_amount,
            ROW_NUMBER() OVER (ORDER BY fare_amount DESC) as rank,
            LAG(fare_amount) OVER (ORDER BY tpep_pickup_datetime) as prev_fare
        FROM nyc_taxi 
        ORDER BY fare_amount DESC 
        LIMIT 20
        """,
        """
        SELECT 
            payment_type,
            fare_amount,
            AVG(fare_amount) OVER (PARTITION BY payment_type) as avg_by_type,
            fare_amount - AVG(fare_amount) OVER (PARTITION BY payment_type) as diff_from_avg
        FROM nyc_taxi 
        LIMIT 50
        """
    ]
    
    INVALID_QUERIES = [
        "SELECT * FRON invalid_table",  # Typo in FROM
        "SELECT COUNT(* FROM table",    # Missing closing parenthesis
        "INSERT INTO VALUES (1, 2)",    # Missing table name
        "UPDATE SET col = 1",           # Missing table name
        "SELECT * FROM",                # Incomplete query
        "INVALID SQL SYNTAX HERE"       # Completely invalid
    ]
    
    QUERIES_WITH_WARNINGS = [
        "SELECT * FROM nyc_taxi",  # Should warn about SELECT *
        "SELECT fare_amount FROM nyc_taxi",  # Should warn about missing LIMIT
        "SELECT payment_type FROM nyc_taxi WHERE 1=1",  # Should warn about scanning entire table
    ]


class ValidationTestCases:
    """Test cases for query validation"""
    
    @staticmethod
    def get_validation_test_cases() -> List[Dict[str, Any]]:
        """Get comprehensive validation test cases"""
        return [
            {
                "name": "valid_simple_select",
                "query": "SELECT * FROM nyc_taxi LIMIT 10",
                "expected_valid": True,
                "expected_type": "SELECT",
                "expected_tables": ["nyc_taxi"],
                "should_have_warnings": True  # SELECT * warning
            },
            {
                "name": "valid_aggregate",
                "query": "SELECT COUNT(*), AVG(fare_amount) FROM nyc_taxi WHERE fare_amount > 0",
                "expected_valid": True,
                "expected_type": "SELECT",
                "expected_tables": ["nyc_taxi"],
                "should_have_warnings": False
            },
            {
                "name": "valid_join",
                "query": "SELECT t1.id, t2.value FROM nyc_taxi t1 JOIN sample_data t2 ON t1.id = t2.id",
                "expected_valid": True,
                "expected_type": "SELECT",
                "expected_tables": ["nyc_taxi", "sample_data"],
                "should_have_warnings": False
            },
            {
                "name": "invalid_syntax",
                "query": "SELECT * FRON invalid_table",
                "expected_valid": False,
                "expected_type": "SELECT",
                "expected_tables": ["invalid_table"],
                "should_have_warnings": False
            },
            {
                "name": "empty_query",
                "query": "",
                "expected_valid": False,
                "expected_type": "UNKNOWN",
                "expected_tables": [],
                "should_have_warnings": False
            },
            {
                "name": "with_query",
                "query": "WITH cte AS (SELECT * FROM nyc_taxi) SELECT * FROM cte LIMIT 5",
                "expected_valid": True,
                "expected_type": "WITH",
                "expected_tables": ["nyc_taxi"],
                "should_have_warnings": False
            }
        ]
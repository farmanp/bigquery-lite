"""
Pytest configuration and fixtures for BigQuery-Lite backend tests
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path():
    """Provide a temporary database path for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    yield tmp_path
    # Clean up
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@pytest.fixture
def mock_clickhouse_client():
    """Mock ClickHouse client for testing"""
    mock_client = Mock()
    mock_client.command = Mock(return_value=1)
    mock_client.query = Mock()
    mock_client.close = Mock()
    return mock_client


@pytest.fixture
def mock_duckdb_connection():
    """Mock DuckDB connection for testing"""
    mock_conn = Mock()
    mock_conn.execute = Mock()
    mock_conn.close = Mock()
    return mock_conn


@pytest.fixture
def sample_sql_queries():
    """Sample SQL queries for testing"""
    return {
        "simple_select": "SELECT * FROM nyc_taxi LIMIT 10",
        "complex_query": """
            SELECT 
                payment_type,
                AVG(fare_amount) as avg_fare,
                COUNT(*) as trip_count
            FROM nyc_taxi 
            WHERE fare_amount > 0 
            GROUP BY payment_type 
            ORDER BY avg_fare DESC
        """,
        "invalid_syntax": "SELECT * FRON invalid_table",
        "window_function": """
            SELECT 
                id,
                fare_amount,
                ROW_NUMBER() OVER (ORDER BY fare_amount DESC) as rank
            FROM nyc_taxi
        """
    }


@pytest.fixture
def sample_query_results():
    """Sample query results for testing"""
    return {
        "simple_data": [
            {"id": 1, "payment_type": "cash", "fare_amount": 15.5},
            {"id": 2, "payment_type": "credit_card", "fare_amount": 22.0},
            {"id": 3, "payment_type": "cash", "fare_amount": 8.75}
        ],
        "aggregated_data": [
            {"payment_type": "credit_card", "avg_fare": 18.5, "trip_count": 150},
            {"payment_type": "cash", "avg_fare": 16.2, "trip_count": 120}
        ]
    }


@pytest.fixture
def clickhouse_env_vars(monkeypatch):
    """Set ClickHouse environment variables for testing"""
    env_vars = {
        "CLICKHOUSE_HOST": "localhost",
        "CLICKHOUSE_PORT": "8123",
        "CLICKHOUSE_USER": "test_user", 
        "CLICKHOUSE_PASSWORD": "test_password"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def performance_metrics_sample():
    """Sample performance metrics for testing"""
    return {
        "execution_time": 0.125,
        "memory_used_mb": 2.5,
        "rows_processed": 1000,
        "cpu_time": 0.075,
        "io_wait": 0.025,
        "network_time": 0.025
    }
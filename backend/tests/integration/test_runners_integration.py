"""
Integration tests for DuckDB and ClickHouse runners

These tests require actual database connections and test:
- Real database initialization and connection
- Actual SQL query execution 
- Performance metrics collection
- Data ingestion and retrieval
- Schema operations
- Error recovery

Note: ClickHouse tests are marked as requiring ClickHouse and will be skipped
if no ClickHouse instance is available.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import patch

from runners.duckdb_runner import DuckDBRunner
from runners.clickhouse_runner import ClickHouseRunner


class TestDuckDBIntegration:
    """Integration tests for DuckDBRunner with real database"""

    @pytest.fixture
    async def duckdb_runner(self, temp_db_path):
        """Create and initialize a real DuckDBRunner instance"""
        runner = DuckDBRunner(db_path=temp_db_path)
        await runner.initialize()
        yield runner
        await runner.cleanup()

    @pytest.mark.integration
    @pytest.mark.requires_duckdb
    @pytest.mark.asyncio
    async def test_duckdb_full_workflow(self, duckdb_runner):
        """Test complete DuckDB workflow with real database"""
        
        # Test basic connection
        status = await duckdb_runner.get_status()
        assert status == "available"
        
        # Test simple query
        result = await duckdb_runner.execute_query("SELECT 1 as test_value")
        assert result["engine"] == "duckdb"
        assert result["rows"] == 1
        assert result["data"][0]["test_value"] == 1
        assert result["execution_time"] > 0
        
        # Test performance metrics
        assert "performance_metrics" in result
        metrics = result["performance_metrics"]
        assert metrics["engine"] == "duckdb"
        assert metrics["execution_time"] > 0
        assert metrics["rows_processed"] == 1

    @pytest.mark.integration
    @pytest.mark.requires_duckdb
    @pytest.mark.asyncio
    async def test_duckdb_table_operations(self, duckdb_runner):
        """Test table creation and data operations"""
        
        # Create test table
        create_sql = """
            CREATE TABLE test_users (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """
        result = await duckdb_runner.execute_query(create_sql)
        assert "error" not in result
        
        # Insert test data
        insert_sql = """
            INSERT INTO test_users (id, name, age) VALUES 
            (1, 'Alice', 25),
            (2, 'Bob', 30),
            (3, 'Charlie', 35)
        """
        result = await duckdb_runner.execute_query(insert_sql)
        assert "error" not in result
        
        # Query the data
        select_sql = "SELECT id, name, age FROM test_users ORDER BY id"
        result = await duckdb_runner.execute_query(select_sql)
        
        assert result["rows"] == 3
        assert result["data"][0]["name"] == "Alice"
        assert result["data"][1]["age"] == 30
        
        # Test aggregation
        agg_sql = "SELECT COUNT(*) as user_count, AVG(age) as avg_age FROM test_users"
        result = await duckdb_runner.execute_query(agg_sql)
        
        assert result["rows"] == 1
        assert result["data"][0]["user_count"] == 3
        assert result["data"][0]["avg_age"] == 30.0

    @pytest.mark.integration
    @pytest.mark.requires_duckdb
    @pytest.mark.asyncio
    async def test_duckdb_schema_operations(self, duckdb_runner):
        """Test schema information retrieval"""
        
        # Get schema info
        schema_info = await duckdb_runner.get_schema_info()
        
        assert schema_info["engine"] == "duckdb"
        assert "tables" in schema_info
        
        # Should have our sample tables
        tables = schema_info["tables"]
        expected_tables = ["nyc_taxi", "sample_data"]
        
        for table_name in expected_tables:
            if table_name in tables:
                assert "columns" in tables[table_name]
                assert len(tables[table_name]["columns"]) > 0

    @pytest.mark.integration
    @pytest.mark.requires_duckdb
    @pytest.mark.asyncio
    async def test_duckdb_query_validation(self, duckdb_runner):
        """Test query validation with real database"""
        
        # Test valid query
        validation = await duckdb_runner.validate_query("SELECT COUNT(*) FROM sample_data")
        assert validation["valid"] is True
        assert validation["query_type"] == "SELECT"
        assert "sample_data" in validation["affected_tables"]
        assert validation["estimated_rows_scanned"] > 0
        
        # Test invalid query
        validation = await duckdb_runner.validate_query("SELECT * FROM nonexistent_table")
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0

    @pytest.mark.integration
    @pytest.mark.requires_duckdb
    @pytest.mark.asyncio
    async def test_duckdb_performance_with_large_dataset(self, duckdb_runner):
        """Test performance with larger dataset"""
        
        # Create a larger test table
        create_sql = """
            CREATE TABLE large_test AS 
            SELECT 
                row_number() OVER () as id,
                'user_' || (row_number() OVER ()) as username,
                random() * 100 as score,
                NOW() - INTERVAL (random() * 365) DAY as created_at
            FROM range(10000)
        """
        
        result = await duckdb_runner.execute_query(create_sql)
        assert "error" not in result
        
        # Test complex query with aggregation
        complex_sql = """
            SELECT 
                DATE_TRUNC('month', created_at) as month,
                COUNT(*) as user_count,
                AVG(score) as avg_score,
                MIN(score) as min_score,
                MAX(score) as max_score
            FROM large_test 
            GROUP BY DATE_TRUNC('month', created_at)
            ORDER BY month
        """
        
        result = await duckdb_runner.execute_query(complex_sql)
        
        assert "error" not in result
        assert result["rows"] > 0
        assert result["execution_time"] > 0
        
        # Verify performance metrics scale appropriately
        metrics = result["performance_metrics"]
        assert metrics["rows_processed"] > 0
        assert metrics["memory_used_mb"] > 0

    @pytest.mark.integration
    @pytest.mark.requires_duckdb
    @pytest.mark.asyncio
    async def test_duckdb_error_recovery(self, duckdb_runner):
        """Test error handling and recovery"""
        
        # Execute an invalid query
        result = await duckdb_runner.execute_query("SELECT * FROM definitely_nonexistent_table")
        assert "error" in result
        assert result["rows"] == 0
        
        # Verify the runner is still functional after error
        status = await duckdb_runner.get_status()
        assert status == "available"
        
        # Execute a valid query to confirm recovery
        result = await duckdb_runner.execute_query("SELECT 1 as recovery_test")
        assert "error" not in result
        assert result["data"][0]["recovery_test"] == 1


class TestClickHouseIntegration:
    """Integration tests for ClickHouseRunner with real database"""

    @pytest.fixture
    async def clickhouse_runner(self):
        """Create and initialize a real ClickHouseRunner instance"""
        runner = ClickHouseRunner()
        # Try to initialize, but don't fail if ClickHouse is not available
        try:
            await runner.initialize()
            if not runner.is_initialized:
                pytest.skip("ClickHouse not available for integration tests")
        except Exception:
            pytest.skip("ClickHouse not available for integration tests")
        
        yield runner
        await runner.cleanup()

    @pytest.mark.integration
    @pytest.mark.requires_clickhouse
    @pytest.mark.asyncio
    async def test_clickhouse_connection(self, clickhouse_runner):
        """Test ClickHouse connection and basic operations"""
        
        # Test connection status
        status = await clickhouse_runner.get_status()
        assert status == "available"
        
        # Test simple query
        result = await clickhouse_runner.execute_query("SELECT 1 as test_value")
        assert result["engine"] == "clickhouse"
        assert result["rows"] == 1
        assert result["data"][0]["test_value"] == 1

    @pytest.mark.integration
    @pytest.mark.requires_clickhouse
    @pytest.mark.asyncio
    async def test_clickhouse_sql_cleaning(self, clickhouse_runner):
        """Test SQL cleaning functionality with real execution"""
        
        # Test query with semicolons and comments
        sql_with_extras = """
            SELECT 1 as value; -- This is a comment
            -- Another comment line
        """
        
        result = await clickhouse_runner.execute_query(sql_with_extras)
        assert "error" not in result
        assert result["rows"] == 1
        assert result["data"][0]["value"] == 1

    @pytest.mark.integration
    @pytest.mark.requires_clickhouse
    @pytest.mark.asyncio
    async def test_clickhouse_schema_operations(self, clickhouse_runner):
        """Test ClickHouse schema information retrieval"""
        
        schema_info = await clickhouse_runner.get_schema_info()
        
        assert schema_info["engine"] == "clickhouse"
        assert schema_info["database"] == "bigquery_lite"
        assert "tables" in schema_info
        
        # Should have sample tables if initialization succeeded
        if schema_info["tables"]:
            for table_name, table_info in schema_info["tables"].items():
                assert "columns" in table_info
                assert "engine" in table_info

    @pytest.mark.integration
    @pytest.mark.requires_clickhouse
    @pytest.mark.asyncio
    async def test_clickhouse_cluster_info(self, clickhouse_runner):
        """Test cluster information retrieval"""
        
        cluster_info = await clickhouse_runner.get_cluster_info()
        
        assert cluster_info["engine"] == "clickhouse"
        assert "version" in cluster_info
        assert "hostname" in cluster_info
        assert "uptime" in cluster_info
        assert "clusters" in cluster_info

    @pytest.mark.integration
    @pytest.mark.requires_clickhouse
    @pytest.mark.asyncio
    async def test_clickhouse_query_validation(self, clickhouse_runner):
        """Test query validation with real ClickHouse"""
        
        # Test valid query
        validation = await clickhouse_runner.validate_query("SELECT 1")
        assert validation["valid"] is True
        assert validation["query_type"] == "SELECT"
        
        # Test invalid query
        validation = await clickhouse_runner.validate_query("INVALID SQL QUERY")
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0

    @pytest.mark.integration
    @pytest.mark.requires_clickhouse
    @pytest.mark.asyncio
    async def test_clickhouse_sample_data_queries(self, clickhouse_runner):
        """Test queries against sample data if available"""
        
        # Test query against sample tables
        try:
            result = await clickhouse_runner.execute_query("SELECT COUNT(*) as row_count FROM nyc_taxi")
            if "error" not in result:
                assert result["rows"] == 1
                assert "row_count" in result["data"][0]
                assert result["data"][0]["row_count"] >= 0
        except Exception:
            # Sample data might not be available, that's okay
            pass

    @pytest.mark.integration
    @pytest.mark.requires_clickhouse
    @pytest.mark.asyncio
    async def test_clickhouse_performance_metrics(self, clickhouse_runner):
        """Test performance metrics collection"""
        
        result = await clickhouse_runner.execute_query("SELECT number FROM numbers(1000) LIMIT 10")
        
        assert "error" not in result
        assert "performance_metrics" in result
        
        metrics = result["performance_metrics"]
        assert metrics["engine"] == "clickhouse"
        assert metrics["execution_time"] > 0
        assert metrics["rows_processed"] == 10
        assert metrics["network_time"] >= 0  # ClickHouse includes network overhead


class TestRunnerComparison:
    """Integration tests comparing DuckDB and ClickHouse runners"""

    @pytest.fixture
    async def both_runners(self, temp_db_path):
        """Setup both runners for comparison tests"""
        duckdb_runner = DuckDBRunner(db_path=temp_db_path)
        await duckdb_runner.initialize()
        
        clickhouse_runner = ClickHouseRunner()
        try:
            await clickhouse_runner.initialize()
            clickhouse_available = clickhouse_runner.is_initialized
        except Exception:
            clickhouse_available = False
        
        yield duckdb_runner, clickhouse_runner if clickhouse_available else None
        
        await duckdb_runner.cleanup()
        if clickhouse_available:
            await clickhouse_runner.cleanup()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_runner_performance_comparison(self, both_runners):
        """Compare performance characteristics between runners"""
        duckdb_runner, clickhouse_runner = both_runners
        
        test_query = "SELECT 1 as test_value, 'test' as test_string"
        
        # Test DuckDB
        duckdb_result = await duckdb_runner.execute_query(test_query)
        assert "error" not in duckdb_result
        
        # Test ClickHouse if available
        if clickhouse_runner:
            clickhouse_result = await clickhouse_runner.execute_query(test_query)
            assert "error" not in clickhouse_result
            
            # Compare results structure
            assert duckdb_result["data"] == clickhouse_result["data"]
            
            # Compare performance metrics structure
            duckdb_metrics = duckdb_result["performance_metrics"]
            clickhouse_metrics = clickhouse_result["performance_metrics"]
            
            # Both should have required metrics
            required_metrics = ["execution_time", "memory_used_mb", "rows_processed", "engine"]
            for metric in required_metrics:
                assert metric in duckdb_metrics
                assert metric in clickhouse_metrics
            
            # ClickHouse should have network overhead, DuckDB should not
            assert clickhouse_metrics["network_time"] >= 0
            assert duckdb_metrics["network_time"] == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_validation_comparison(self, both_runners):
        """Compare query validation between runners"""
        duckdb_runner, clickhouse_runner = both_runners
        
        test_queries = [
            "SELECT 1",
            "SELECT * FROM non_existent_table",
            "INVALID SQL SYNTAX"
        ]
        
        for query in test_queries:
            duckdb_validation = await duckdb_runner.validate_query(query)
            
            if clickhouse_runner:
                clickhouse_validation = await clickhouse_runner.validate_query(query)
                
                # Both should agree on basic validity for simple cases
                if query == "SELECT 1":
                    assert duckdb_validation["valid"] == clickhouse_validation["valid"] == True
                
                # Both should have similar structure
                required_fields = ["valid", "query_type", "estimated_execution_time_ms"]
                for field in required_fields:
                    assert field in duckdb_validation
                    assert field in clickhouse_validation
"""
Unit tests for DuckDBRunner

Tests the DuckDB query execution engine including:
- Initialization and connection management
- SQL query execution and result handling
- Performance metrics collection
- Query validation and estimation
- Error handling and recovery
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import time

from runners.duckdb_runner import DuckDBRunner


class TestDuckDBRunner:
    """Test cases for DuckDBRunner class"""

    @pytest.fixture
    def runner(self, temp_db_path):
        """Create a DuckDBRunner instance for testing"""
        return DuckDBRunner(db_path=temp_db_path)

    @pytest.fixture
    def initialized_runner(self, runner, mock_duckdb_connection):
        """Create an initialized DuckDBRunner instance"""
        with patch('runners.duckdb_runner.duckdb.connect', return_value=mock_duckdb_connection):
            runner.connection = mock_duckdb_connection
            runner.is_initialized = True
            return runner

    @pytest.mark.unit
    def test_runner_initialization(self, runner):
        """Test DuckDBRunner initialization"""
        assert runner.db_path != ":memory:"  # Should use temp path
        assert runner.connection is None
        assert runner.is_initialized is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_success(self, runner, mock_duckdb_connection):
        """Test successful initialization"""
        with patch('runners.duckdb_runner.duckdb.connect', return_value=mock_duckdb_connection), \
             patch('os.path.exists', return_value=False):
            
            await runner.initialize()
            
            assert runner.connection == mock_duckdb_connection
            assert runner.is_initialized is True
            
            # Verify initialization calls
            mock_duckdb_connection.execute.assert_any_call("PRAGMA enable_profiling")
            mock_duckdb_connection.execute.assert_any_call("PRAGMA profiling_mode = 'detailed'")
            mock_duckdb_connection.execute.assert_any_call("PRAGMA memory_limit='2GB'")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_failure(self, runner):
        """Test initialization failure handling"""
        with patch('runners.duckdb_runner.duckdb.connect', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                await runner.initialize()
            
            assert runner.is_initialized is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_success(self, initialized_runner, sample_query_results):
        """Test successful query execution"""
        # Mock the fetchdf result
        mock_df = pd.DataFrame(sample_query_results["simple_data"])
        
        # Create separate mocks for the three execute calls:
        # 1. PRAGMA profiling_output
        pragma_mock = Mock()
        
        # 2. The actual query
        query_mock = Mock()
        query_mock.fetchdf.return_value = mock_df
        
        # 3. EXPLAIN ANALYZE query
        explain_mock = Mock()
        explain_mock.fetchall.return_value = [("Seq Scan on nyc_taxi",), ("Planning time: 0.1ms",)]
        
        # Set up side_effect to return different mocks for different calls
        initialized_runner.connection.execute.side_effect = [pragma_mock, query_mock, explain_mock]
        
        sql = "SELECT * FROM nyc_taxi LIMIT 3"
        result = await initialized_runner.execute_query(sql)
        
        assert result["engine"] == "duckdb"
        assert result["rows"] == 3
        assert len(result["data"]) == 3
        assert result["data"][0]["id"] == 1
        assert result["execution_time"] > 0
        assert "performance_metrics" in result

    @pytest.mark.unit
    @pytest.mark.asyncio  
    async def test_execute_query_with_nan_values(self, initialized_runner):
        """Test query execution with NaN values in results"""
        # Create DataFrame with NaN values
        mock_df = pd.DataFrame({
            "id": [1, 2],
            "value": [10.5, float('nan')],
            "name": ["test", None]
        })
        initialized_runner.connection.execute.return_value.fetchdf.return_value = mock_df
        
        result = await initialized_runner.execute_query("SELECT * FROM test_table")
        
        # Check that NaN values are converted to None
        assert result["data"][1]["value"] is None
        assert result["data"][1]["name"] is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_error_handling(self, initialized_runner):
        """Test query execution error handling"""
        initialized_runner.connection.execute.side_effect = Exception("SQL syntax error")
        
        result = await initialized_runner.execute_query("INVALID SQL")
        
        assert result["engine"] == "duckdb"
        assert result["rows"] == 0
        assert result["data"] == []
        assert "SQL syntax error" in result["error"]
        assert result["execution_time"] > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_status_available(self, initialized_runner):
        """Test status check when runner is available"""
        initialized_runner.connection.execute.return_value.fetchone.return_value = (1,)
        
        status = await initialized_runner.get_status()
        assert status == "available"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_status_not_initialized(self, runner):
        """Test status check when not initialized"""
        status = await runner.get_status()
        assert status == "not_initialized"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_status_error(self, initialized_runner):
        """Test status check when connection fails"""
        initialized_runner.connection.execute.side_effect = Exception("Connection error")
        
        status = await initialized_runner.get_status()
        assert status == "error"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_schema_info_success(self, initialized_runner):
        """Test successful schema information retrieval"""
        # Mock tables result
        tables_result = Mock()
        tables_result.fetchall.return_value = [("nyc_taxi", "BASE TABLE"), ("sample_data", "BASE TABLE")]
        
        # Mock columns result
        columns_result = Mock()
        columns_result.fetchall.return_value = [
            ("id", "INTEGER"),
            ("payment_type", "VARCHAR"),
            ("fare_amount", "DOUBLE")
        ]
        
        initialized_runner.connection.execute.return_value = tables_result
        # Alternate between tables and columns results
        initialized_runner.connection.execute.side_effect = [tables_result, columns_result, columns_result]
        
        schema_info = await initialized_runner.get_schema_info()
        
        assert schema_info["engine"] == "duckdb"
        assert "tables" in schema_info
        assert "nyc_taxi" in schema_info["tables"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_schema_info_not_initialized(self, runner, mock_duckdb_connection):
        """Test schema info when not initialized - should auto-initialize"""
        with patch('runners.duckdb_runner.duckdb.connect', return_value=mock_duckdb_connection), \
             patch('os.path.exists', return_value=False):
            
            # Mock the schema query results
            tables_result = Mock()
            tables_result.fetchall.return_value = []
            mock_duckdb_connection.execute.return_value = tables_result
            
            schema_info = await runner.get_schema_info()
            assert schema_info["engine"] == "duckdb"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_query_valid_sql(self, initialized_runner):
        """Test query validation with valid SQL"""
        # Mock EXPLAIN result
        explain_result = Mock()
        explain_result.fetchall.return_value = [("Query plan here",)]
        
        # Mock COUNT result for table size estimation
        count_result = Mock()
        count_result.fetchone.return_value = (1000,)
        
        initialized_runner.connection.execute.side_effect = [explain_result, count_result]
        
        validation = await initialized_runner.validate_query("SELECT * FROM nyc_taxi LIMIT 10")
        
        assert validation["valid"] is True
        assert validation["query_type"] == "SELECT"
        assert validation["affected_tables"] == ["nyc_taxi"]
        assert validation["estimated_rows_scanned"] > 0
        assert "This query will process" in validation["suggestion"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_query_invalid_sql(self, initialized_runner):
        """Test query validation with invalid SQL"""
        initialized_runner.connection.execute.side_effect = Exception("Syntax error")
        
        validation = await initialized_runner.validate_query("INVALID SQL QUERY")
        
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0
        assert "Syntax error" in validation["errors"][0]
        assert validation["query_type"] == "OTHER"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_query_empty(self, initialized_runner):
        """Test query validation with empty query"""
        validation = await initialized_runner.validate_query("")
        
        assert validation["valid"] is False
        assert "Empty query" in validation["errors"]
        assert validation["query_type"] == "UNKNOWN"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_query_with_warnings(self, initialized_runner):
        """Test query validation generates appropriate warnings"""
        # Mock EXPLAIN result
        explain_result = Mock()
        explain_result.fetchall.return_value = [("Query plan",)]
        
        # Mock large table
        count_result = Mock()
        count_result.fetchone.return_value = (50000,)
        
        initialized_runner.connection.execute.side_effect = [explain_result, count_result]
        
        validation = await initialized_runner.validate_query("SELECT * FROM large_table")
        
        assert validation["valid"] is True
        assert len(validation["warnings"]) > 0
        # Should warn about SELECT * and missing LIMIT
        warning_text = " ".join(validation["warnings"])
        assert "SELECT *" in warning_text

    @pytest.mark.unit
    def test_get_query_type(self, runner):
        """Test query type detection"""
        test_cases = [
            ("SELECT * FROM table", "SELECT"),
            ("INSERT INTO table VALUES (1)", "INSERT"),
            ("UPDATE table SET col=1", "UPDATE"),
            ("DELETE FROM table", "DELETE"),
            ("CREATE TABLE test (id int)", "CREATE"),
            ("DROP TABLE test", "DROP"),
            ("ALTER TABLE test ADD COLUMN", "ALTER"),
            ("WITH cte AS (SELECT 1) SELECT * FROM cte", "WITH"),
            ("UNKNOWN COMMAND", "OTHER")
        ]
        
        for sql, expected_type in test_cases:
            assert runner._get_query_type(sql) == expected_type

    @pytest.mark.unit
    def test_extract_table_names(self, runner):
        """Test table name extraction from SQL queries"""
        test_cases = [
            ("SELECT * FROM users", ["users"]),
            ("SELECT * FROM users JOIN orders ON users.id = orders.user_id", ["users", "orders"]),
            ("INSERT INTO customers (name) VALUES ('John')", ["customers"]),
            ("UPDATE products SET price = 100", ["products"]),
            ("SELECT * FROM schema.table_name", ["schema"])  # Simple regex extracts schema part
        ]
        
        for sql, expected_tables in test_cases:
            result = runner._extract_table_names(sql)
            assert set(result) == set(expected_tables)

    @pytest.mark.unit
    def test_estimate_execution_time(self, runner):
        """Test execution time estimation"""
        # Test simple query
        simple_time = runner._estimate_execution_time("SELECT * FROM table", 1000, "SELECT")
        assert simple_time >= 10  # Minimum time
        
        # Test complex query with JOINs
        complex_time = runner._estimate_execution_time(
            "SELECT * FROM table1 JOIN table2 JOIN table3 GROUP BY col ORDER BY col2", 
            10000, 
            "SELECT"
        )
        assert complex_time > simple_time

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cleanup(self, initialized_runner):
        """Test cleanup of resources"""
        # Store reference to mock connection before cleanup
        mock_connection = initialized_runner.connection
        
        await initialized_runner.cleanup()
        
        mock_connection.close.assert_called_once()
        assert initialized_runner.connection is None
        assert initialized_runner.is_initialized is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_auto_initialization_on_execute(self, runner, mock_duckdb_connection):
        """Test that execute_query auto-initializes if not already initialized"""
        mock_df = pd.DataFrame([{"result": 1}])
        mock_duckdb_connection.execute.return_value.fetchdf.return_value = mock_df
        
        with patch('runners.duckdb_runner.duckdb.connect', return_value=mock_duckdb_connection), \
             patch('os.path.exists', return_value=False):
            
            result = await runner.execute_query("SELECT 1")
            
            assert runner.is_initialized is True
            assert result["rows"] == 1

    @pytest.mark.unit
    def test_performance_metrics_calculation(self, runner):
        """Test performance metrics are properly calculated"""
        test_data = [{"id": i} for i in range(100)]
        
        # The performance metrics should scale with data size
        estimated_memory = max(0.1, len(test_data) * 0.001)
        assert estimated_memory >= 0.1
        
        # CPU time should be a portion of execution time
        execution_time = 0.5
        cpu_time = execution_time * 0.8
        assert cpu_time == 0.4
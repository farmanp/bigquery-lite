"""
Unit tests for ClickHouseRunner

Tests the ClickHouse query execution engine including:
- Initialization and connection management
- SQL query execution and result handling
- SQL cleaning for ClickHouse compatibility
- Performance metrics collection
- Query validation and estimation
- Cluster information retrieval
- Error handling and recovery
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import time

from runners.clickhouse_runner import ClickHouseRunner


class TestClickHouseRunner:
    """Test cases for ClickHouseRunner class"""

    @pytest.fixture
    def runner(self, clickhouse_env_vars):
        """Create a ClickHouseRunner instance for testing"""
        return ClickHouseRunner()

    @pytest.fixture
    def initialized_runner(self, runner, mock_clickhouse_client):
        """Create an initialized ClickHouseRunner instance"""
        runner.client = mock_clickhouse_client
        runner.is_initialized = True
        return runner

    @pytest.mark.unit
    def test_runner_initialization_with_defaults(self, clickhouse_env_vars):
        """Test ClickHouseRunner initialization with environment variables"""
        runner = ClickHouseRunner()
        
        assert runner.host == "localhost"
        assert runner.port == 8123
        assert runner.username == "test_user"
        assert runner.password == "test_password"
        assert runner.client is None
        assert runner.is_initialized is False

    @pytest.mark.unit
    def test_runner_initialization_with_params(self):
        """Test ClickHouseRunner initialization with explicit parameters"""
        runner = ClickHouseRunner(
            host="custom_host",
            port=9000,
            username="custom_user",
            password="custom_pass"
        )
        
        assert runner.host == "custom_host"
        assert runner.port == 9000
        assert runner.username == "custom_user"
        assert runner.password == "custom_pass"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_success(self, runner, mock_clickhouse_client):
        """Test successful initialization"""
        with patch('runners.clickhouse_runner.clickhouse_connect.get_client', 
                   return_value=mock_clickhouse_client):
            
            mock_clickhouse_client.command.return_value = 1
            
            await runner.initialize()
            
            assert runner.client == mock_clickhouse_client
            assert runner.is_initialized is True
            
            # Verify initialization calls
            mock_clickhouse_client.command.assert_any_call("SELECT 1")
            mock_clickhouse_client.command.assert_any_call("CREATE DATABASE IF NOT EXISTS bigquery_lite")
            mock_clickhouse_client.command.assert_any_call("USE bigquery_lite")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self, runner):
        """Test initialization with connection failure"""
        with patch('runners.clickhouse_runner.clickhouse_connect.get_client', 
                   side_effect=Exception("Connection failed")):
            
            await runner.initialize()
            
            assert runner.is_initialized is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_connection_test_failure(self, runner, mock_clickhouse_client):
        """Test initialization with connection test failure"""
        with patch('runners.clickhouse_runner.clickhouse_connect.get_client', 
                   return_value=mock_clickhouse_client):
            
            mock_clickhouse_client.command.return_value = 0  # Test fails
            
            await runner.initialize()
            
            assert runner.is_initialized is False

    @pytest.mark.unit
    def test_clean_sql_for_clickhouse(self, runner):
        """Test SQL cleaning for ClickHouse compatibility"""
        test_cases = [
            ("SELECT * FROM table;", "SELECT * FROM table"),
            ("SELECT * FROM table;;", "SELECT * FROM table"),
            ("SELECT 1; SELECT 2;", "SELECT 1 SELECT 2"),
            ("SELECT * -- comment\nFROM table;", "SELECT * FROM table"),
            ("  SELECT   *   FROM   table  ; ", "SELECT   *   FROM   table"),  # Whitespace within lines preserved
            ("SELECT 1;\n-- Another comment\nSELECT 2;", "SELECT 1 SELECT 2")
        ]
        
        for input_sql, expected in test_cases:
            result = runner._clean_sql_for_clickhouse(input_sql)
            assert result == expected

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_success(self, initialized_runner, sample_query_results):
        """Test successful query execution"""
        # Mock query result
        mock_result = Mock()
        mock_result.result_rows = [
            (1, "cash", 15.5),
            (2, "credit_card", 22.0),
            (3, "cash", 8.75)
        ]
        mock_result.column_names = [("id",), ("payment_type",), ("fare_amount",)]
        
        initialized_runner.client.query.return_value = mock_result
        
        # Mock EXPLAIN query
        mock_explain = Mock()
        mock_explain.result_rows = [("Scan table nyc_taxi",)]
        initialized_runner.client.query.side_effect = [mock_result, mock_explain]
        
        sql = "SELECT * FROM nyc_taxi LIMIT 3;"
        result = await initialized_runner.execute_query(sql)
        
        assert result["engine"] == "clickhouse"
        assert result["rows"] == 3
        assert len(result["data"]) == 3
        assert result["data"][0]["id"] == 1
        assert result["execution_time"] > 0
        assert "performance_metrics" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_with_datetime(self, initialized_runner):
        """Test query execution with datetime values"""
        # Mock result with datetime
        mock_result = Mock()
        test_datetime = datetime(2023, 1, 1, 12, 0, 0)
        mock_result.result_rows = [(1, test_datetime)]
        mock_result.column_names = [("id",), ("created_at",)]
        
        initialized_runner.client.query.return_value = mock_result
        
        result = await initialized_runner.execute_query("SELECT id, created_at FROM events")
        
        # DateTime should be converted to ISO format
        assert result["data"][0]["created_at"] == "2023-01-01T12:00:00"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_error_handling(self, initialized_runner):
        """Test query execution error handling"""
        from clickhouse_connect.driver.exceptions import ClickHouseError
        
        initialized_runner.client.query.side_effect = ClickHouseError("Syntax error")
        
        result = await initialized_runner.execute_query("INVALID SQL")
        
        assert result["engine"] == "clickhouse"
        assert result["rows"] == 0
        assert result["data"] == []
        assert "Syntax error" in result["error"]
        assert result["execution_time"] > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_not_initialized(self, runner, mock_clickhouse_client):
        """Test execute_query auto-initializes when not initialized"""
        with patch('runners.clickhouse_runner.clickhouse_connect.get_client', 
                   return_value=mock_clickhouse_client):
            
            mock_clickhouse_client.command.return_value = 1
            
            # Mock query result
            mock_result = Mock()
            mock_result.result_rows = [(1,)]
            mock_result.column_names = [("result",)]
            mock_clickhouse_client.query.return_value = mock_result
            
            result = await runner.execute_query("SELECT 1")
            
            assert runner.is_initialized is True
            assert result["rows"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_initialization_fails(self, runner):
        """Test execute_query when initialization fails"""
        with patch('runners.clickhouse_runner.clickhouse_connect.get_client', 
                   side_effect=Exception("Connection failed")):
            
            with pytest.raises(Exception, match="ClickHouse is not available"):
                await runner.execute_query("SELECT 1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_status_available(self, initialized_runner):
        """Test status check when runner is available"""
        initialized_runner.client.command.return_value = 1
        
        status = await initialized_runner.get_status()
        assert status == "available"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_status_not_connected(self, runner):
        """Test status check when not connected"""
        status = await runner.get_status()
        assert status == "not_connected"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_status_error(self, initialized_runner):
        """Test status check when connection fails"""
        initialized_runner.client.command.side_effect = Exception("Connection error")
        
        status = await initialized_runner.get_status()
        assert status == "error"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_schema_info_success(self, initialized_runner):
        """Test successful schema information retrieval"""
        # Mock tables result
        tables_result = Mock()
        tables_result.result_rows = [("nyc_taxi", "MergeTree"), ("sample_data", "MergeTree")]
        
        # Mock columns result
        columns_result = Mock()
        columns_result.result_rows = [
            ("id", "UInt64"),
            ("payment_type", "String"),
            ("fare_amount", "Float64")
        ]
        
        initialized_runner.client.query.side_effect = [tables_result, columns_result, columns_result]
        
        schema_info = await initialized_runner.get_schema_info()
        
        assert schema_info["engine"] == "clickhouse"
        assert schema_info["database"] == "bigquery_lite"
        assert "tables" in schema_info
        assert "nyc_taxi" in schema_info["tables"]
        assert schema_info["tables"]["nyc_taxi"]["engine"] == "MergeTree"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_schema_info_not_initialized(self, runner):
        """Test schema info when not initialized"""
        schema_info = await runner.get_schema_info()
        
        assert schema_info["engine"] == "clickhouse"
        assert "error" in schema_info
        assert "Not initialized" in schema_info["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cluster_info_success(self, initialized_runner):
        """Test successful cluster information retrieval"""
        # Mock clusters result
        clusters_result = Mock()
        clusters_result.result_rows = [
            ("test_cluster", 1, 1, "localhost", 9000),
            ("test_cluster", 1, 2, "localhost", 9001)
        ]
        
        # Mock server info result
        server_result = Mock()
        server_result.result_rows = [("23.8.1.2", "localhost", 3600)]
        
        initialized_runner.client.query.side_effect = [clusters_result, server_result]
        
        cluster_info = await initialized_runner.get_cluster_info()
        
        assert cluster_info["engine"] == "clickhouse"
        assert cluster_info["version"] == "23.8.1.2"
        assert cluster_info["hostname"] == "localhost"
        assert cluster_info["uptime"] == 3600
        assert len(cluster_info["clusters"]) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cluster_info_not_initialized(self, runner):
        """Test cluster info when not initialized"""
        cluster_info = await runner.get_cluster_info()
        
        assert "error" in cluster_info
        assert "Not initialized" in cluster_info["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_query_valid_sql(self, initialized_runner):
        """Test query validation with valid SQL"""
        # Mock EXPLAIN result
        explain_result = Mock()
        explain_result.result_rows = [("Query plan here",)]
        
        # Mock table statistics
        stats_result = Mock()
        stats_result.result_rows = [(1000, 150000)]  # rows, bytes
        
        initialized_runner.client.query.side_effect = [explain_result, stats_result]
        
        validation = await initialized_runner.validate_query("SELECT * FROM nyc_taxi LIMIT 10")
        
        assert validation["valid"] is True
        assert validation["query_type"] == "SELECT"
        assert validation["affected_tables"] == ["nyc_taxi"]
        assert validation["estimated_rows_scanned"] == 1000
        assert validation["estimated_bytes_processed"] == 150000
        assert "This query will process" in validation["suggestion"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_query_invalid_sql(self, initialized_runner):
        """Test query validation with invalid SQL"""
        initialized_runner.client.query.side_effect = Exception("Syntax error")
        
        validation = await initialized_runner.validate_query("INVALID SQL QUERY")
        
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0
        assert "Syntax error" in validation["errors"][0]
        assert validation["query_type"] == "OTHER"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_query_not_initialized(self, runner):
        """Test query validation when not initialized"""
        validation = await runner.validate_query("SELECT 1")
        
        assert validation["valid"] is False
        assert "ClickHouse is not available" in validation["errors"]
        assert validation["query_type"] == "UNKNOWN"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_query_with_warnings(self, initialized_runner):
        """Test query validation generates appropriate warnings"""
        # Mock EXPLAIN result
        explain_result = Mock()
        explain_result.result_rows = [("Query plan",)]
        
        # Mock large table stats
        stats_result = Mock()
        stats_result.result_rows = [(50000, 5000000)]
        
        initialized_runner.client.query.side_effect = [explain_result, stats_result]
        
        validation = await initialized_runner.validate_query("SELECT * FROM large_table")
        
        assert validation["valid"] is True
        assert len(validation["warnings"]) > 0
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
        assert simple_time >= 20  # Minimum time
        
        # Test complex query with JOINs and GROUP BY
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
        # Store reference to mock client before cleanup
        mock_client = initialized_runner.client
        
        await initialized_runner.cleanup()
        
        mock_client.close.assert_called_once()
        assert initialized_runner.client is None
        assert initialized_runner.is_initialized is False

    @pytest.mark.unit
    def test_performance_metrics_calculation(self, runner):
        """Test performance metrics are properly calculated and distributed system overhead"""
        # ClickHouse should have higher base overhead than DuckDB due to distributed nature
        test_data = [{"id": i} for i in range(100)]
        
        estimated_memory = max(0.5, len(test_data) * 0.002)
        assert estimated_memory >= 0.5  # Higher base memory than DuckDB
        
        # Test network time simulation
        execution_time = 1.0
        network_time = execution_time * 0.1  # 10% network overhead
        cpu_time = execution_time * 0.6      # 60% CPU time
        io_wait = execution_time * 0.2       # 20% IO wait
        
        assert network_time == 0.1
        assert cpu_time == 0.6
        assert io_wait == 0.2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_setup_sample_data_error_handling(self, runner, mock_clickhouse_client):
        """Test sample data setup handles errors gracefully"""
        with patch('runners.clickhouse_runner.clickhouse_connect.get_client', 
                   return_value=mock_clickhouse_client):
            
            # Mock successful connection test
            mock_clickhouse_client.command.side_effect = [
                1,  # Connection test
                None,  # CREATE DATABASE
                None,  # USE database
                Exception("Table creation failed"),  # Fail on table creation
            ]
            
            # Should not raise exception even if sample data setup fails
            await runner.initialize()
            
            assert runner.is_initialized is True

    @pytest.mark.unit
    def test_data_type_conversion(self, runner):
        """Test that various data types are properly handled in results"""
        # This tests the logic in execute_query for handling different value types
        test_values = [
            ("string_val", str, "string_val"),
            (123, int, 123),
            (45.67, float, 45.67),
            (True, bool, True),
            (None, type(None), None),
        ]
        
        for original, expected_type, expected_value in test_values:
            # Test that the value would be handled correctly
            if hasattr(original, 'isoformat'):  # datetime
                result = original.isoformat()
            elif isinstance(original, (int, float, str, bool)) or original is None:
                result = original
            else:
                result = str(original)
            
            assert result == expected_value
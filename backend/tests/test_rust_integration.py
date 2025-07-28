#!/usr/bin/env python3
"""
Integration tests for Rust BlazeQueryEngine Python bindings

Tests the FFI interface, error handling, and integration with existing backend.
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try to import Rust engine
try:
    import bigquery_lite_engine
    RUST_ENGINE_AVAILABLE = True
except ImportError:
    RUST_ENGINE_AVAILABLE = False


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestRustEngineBasics:
    """Test basic Rust engine functionality through Python bindings"""
    
    def test_engine_creation(self):
        """Test creating a new engine instance"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        assert engine is not None
        
        stats = engine.get_stats_sync()
        assert stats.total_queries == 0
        assert stats.registered_tables == 0
        assert stats.avg_execution_time_ms == 0.0
    
    def test_convenience_function(self):
        """Test the convenience function for creating engines"""
        engine = bigquery_lite_engine.create_engine()
        assert engine is not None
    
    def test_test_data_registration(self):
        """Test registering test data"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        # Register test data
        engine.register_test_data("test_table", 1000)
        
        # Verify table is registered
        tables = engine.list_tables_sync()
        assert "test_table" in tables
        
        stats = engine.get_stats_sync()
        assert stats.registered_tables == 1
    
    def test_basic_query_execution(self):
        """Test executing basic SQL queries"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("basic_test", 100)
        
        # Simple count query
        result = engine.execute_query_sync("SELECT COUNT(*) FROM basic_test")
        
        assert result.rows == 1
        assert result.execution_time_ms >= 0
        assert result.memory_used_bytes >= 0
        assert result.engine == "blaze"
        
        # Check data format
        data = result.data
        assert len(data) == 1
        assert "COUNT(*)" in data[0]
        assert data[0]["COUNT(*)"] == 100
    
    def test_aggregation_queries(self):
        """Test GROUP BY and aggregation queries"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("agg_test", 1000)
        
        result = engine.execute_query_sync(
            "SELECT category, COUNT(*) as count, AVG(value) as avg_value "
            "FROM agg_test GROUP BY category ORDER BY category"
        )
        
        assert result.rows == 10  # Should have 10 categories (0-9)
        assert len(result.data) == 10
        
        # Verify data structure
        first_row = result.data[0]
        assert "category" in first_row
        assert "count" in first_row
        assert "avg_value" in first_row
        
        # Verify categories are ordered
        categories = [row["category"] for row in result.data]
        assert categories == sorted(categories)
    
    def test_filtering_and_limits(self):
        """Test WHERE clauses and LIMIT"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("filter_test", 1000)
        
        result = engine.execute_query_sync(
            "SELECT * FROM filter_test WHERE value > 500 ORDER BY value DESC LIMIT 5"
        )
        
        assert result.rows <= 5
        assert len(result.data) <= 5
        
        # Verify filtering worked (all values > 500)
        for row in result.data:
            assert row["value"] > 500
        
        # Verify ordering (descending)
        if len(result.data) > 1:
            values = [row["value"] for row in result.data]
            assert values == sorted(values, reverse=True)


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestRustEnginePerformance:
    """Test performance characteristics of the Rust engine"""
    
    def test_small_dataset_performance(self):
        """Test performance with small datasets"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("small_perf", 1000)
        
        start_time = time.time()
        result = engine.execute_query_sync("SELECT COUNT(*) FROM small_perf")
        total_time = time.time() - start_time
        
        # Should be very fast
        assert result.execution_time_ms < 100  # Less than 100ms
        assert total_time < 1.0  # Total time including Python overhead
    
    def test_large_dataset_performance(self):
        """Test performance with larger datasets"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("large_perf", 100_000)
        
        start_time = time.time()
        result = engine.execute_query_sync(
            "SELECT category, COUNT(*), AVG(value), SUM(value) FROM large_perf GROUP BY category"
        )
        total_time = time.time() - start_time
        
        # Should still be reasonably fast
        assert result.execution_time_ms < 500  # Less than 500ms
        assert total_time < 2.0  # Total time including Python overhead
        assert result.rows == 10  # 10 categories
    
    def test_memory_efficiency(self):
        """Test memory usage is reasonable"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("memory_test", 50_000)
        
        result = engine.execute_query_sync(
            "SELECT category, COUNT(*), AVG(value) FROM memory_test GROUP BY category"
        )
        
        # Memory usage should be reasonable (less than 100MB for this test)
        assert result.memory_used_bytes < 100 * 1024 * 1024
    
    def test_performance_regression(self):
        """Test that performance doesn't regress over multiple queries"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("regression_test", 10_000)
        
        times = []
        for i in range(10):
            start_time = time.time()
            result = engine.execute_query_sync(f"SELECT COUNT(*) FROM regression_test WHERE value > {i * 100}")
            execution_time = time.time() - start_time
            times.append(execution_time)
        
        # Later queries shouldn't be significantly slower than early ones
        early_avg = sum(times[:3]) / 3
        late_avg = sum(times[-3:]) / 3
        
        # Allow up to 2x slower (accounts for JIT warmup, caching effects)
        assert late_avg < early_avg * 2


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestRustEngineErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_sql_syntax(self):
        """Test handling of invalid SQL"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        with pytest.raises(Exception):
            engine.execute_query_sync("INVALID SQL SYNTAX")
    
    def test_nonexistent_table(self):
        """Test querying non-existent tables"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        with pytest.raises(Exception):
            engine.execute_query_sync("SELECT * FROM nonexistent_table")
    
    def test_query_validation(self):
        """Test SQL query validation"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("validation_test", 100)
        
        # Valid query
        assert engine.validate_query_sync("SELECT * FROM validation_test") == True
        
        # Invalid query
        assert engine.validate_query_sync("INVALID SQL") == False
    
    def test_empty_result_handling(self):
        """Test handling of queries with empty results"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("empty_test", 1000)
        
        # Query that returns no rows
        result = engine.execute_query_sync("SELECT * FROM empty_test WHERE value > 10000")
        
        assert result.rows == 0
        assert len(result.data) == 0
        assert result.execution_time_ms >= 0


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestRustEngineConcurrency:
    """Test concurrent usage of the Rust engine"""
    
    def test_thread_safety(self):
        """Test that the engine is thread-safe"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("thread_test", 10_000)
        
        def run_query(query_id):
            try:
                result = engine.execute_query_sync(
                    f"SELECT COUNT(*) FROM thread_test WHERE value > {query_id * 100}"
                )
                return result.rows
            except Exception as e:
                return f"Error: {e}"
        
        # Run multiple queries concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_query, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        # All queries should succeed
        for result in results:
            assert isinstance(result, int), f"Query failed: {result}"
            assert result >= 0
    
    def test_multiple_engines(self):
        """Test using multiple engine instances"""
        engines = [bigquery_lite_engine.BlazeQueryEngine() for _ in range(3)]
        
        # Register data in each engine
        for i, engine in enumerate(engines):
            engine.register_test_data(f"multi_test_{i}", 1000)
        
        # Query each engine
        results = []
        for i, engine in enumerate(engines):
            result = engine.execute_query_sync(f"SELECT COUNT(*) FROM multi_test_{i}")
            results.append(result.rows)
        
        # All should return the expected count
        assert all(r == 1 for r in results)


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestRustEngineDataTypes:
    """Test handling of different data types"""
    
    def test_numeric_data_types(self):
        """Test that numeric data types are handled correctly"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("numeric_test", 100)
        
        result = engine.execute_query_sync(
            "SELECT MIN(value), MAX(value), AVG(value), SUM(value) FROM numeric_test"
        )
        
        assert result.rows == 1
        row = result.data[0]
        
        # Check that all values are numeric
        assert isinstance(row["MIN(numeric_test.value)"], (int, float))
        assert isinstance(row["MAX(numeric_test.value)"], (int, float))
        assert isinstance(row["AVG(numeric_test.value)"], (int, float))
        assert isinstance(row["SUM(numeric_test.value)"], (int, float))
    
    def test_string_data_types(self):
        """Test that string data types are handled correctly"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("string_test", 100)
        
        result = engine.execute_query_sync(
            "SELECT DISTINCT category FROM string_test ORDER BY category LIMIT 5"
        )
        
        assert result.rows <= 5
        
        # Check that category values are strings
        for row in result.data:
            assert isinstance(row["category"], str)
            assert row["category"].startswith("category_")


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestRustEngineIntegration:
    """Test integration with existing backend components"""
    
    def test_result_format_compatibility(self):
        """Test that result format is compatible with existing code"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("format_test", 100)
        
        result = engine.execute_query_sync("SELECT COUNT(*) as total FROM format_test")
        
        # Should have expected attributes
        assert hasattr(result, 'rows')
        assert hasattr(result, 'execution_time_ms')
        assert hasattr(result, 'memory_used_bytes')
        assert hasattr(result, 'engine')
        assert hasattr(result, 'data')
        
        # Data should be a list of dictionaries
        assert isinstance(result.data, list)
        assert len(result.data) == 1
        assert isinstance(result.data[0], dict)
        assert "total" in result.data[0]
    
    def test_stats_tracking(self):
        """Test that statistics are tracked correctly"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("stats_test", 100)
        
        # Execute multiple queries
        queries_run = 5
        for i in range(queries_run):
            engine.execute_query_sync(f"SELECT COUNT(*) FROM stats_test WHERE value > {i * 100}")
        
        stats = engine.get_stats_sync()
        
        assert stats.total_queries == queries_run
        assert stats.avg_execution_time_ms > 0
        assert stats.registered_tables == 1
        assert stats.peak_memory_bytes >= 0


if __name__ == "__main__":
    if RUST_ENGINE_AVAILABLE:
        print("✅ Rust engine available - running tests")
        pytest.main([__file__, "-v"])
    else:
        print("❌ Rust engine not available - skipping tests")
        print("Build the engine with: cd bigquery-lite-engine && maturin develop --release")
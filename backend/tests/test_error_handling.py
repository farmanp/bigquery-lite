#!/usr/bin/env python3
"""
Error handling and edge case tests for Rust engine

These tests ensure the engine handles errors gracefully and provides
meaningful error messages for various failure scenarios.
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Try to import Rust engine
try:
    import bigquery_lite_engine
    RUST_ENGINE_AVAILABLE = True
except ImportError:
    RUST_ENGINE_AVAILABLE = False


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestSQLErrorHandling:
    """Test handling of various SQL syntax and semantic errors"""
    
    def test_invalid_sql_syntax(self):
        """Test handling of malformed SQL"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        invalid_queries = [
            "SELECT * FORM table",  # typo in FROM
            "SELECT COUNT() FROM test",  # missing asterisk
            "SELECT * FROM WHERE id = 1",  # missing table name
            "INSERT INTO test VALUES",  # incomplete INSERT
            "SELECT * FROM test ORDER",  # incomplete ORDER BY
            "SELECT * FROM test GROUP",  # incomplete GROUP BY
            "INVALID SQL SYNTAX",  # completely invalid
            "",  # empty query
            "   ",  # whitespace only
        ]
        
        for query in invalid_queries:
            with pytest.raises(Exception, match=r".*"):
                engine.execute_query_sync(query)
    
    def test_nonexistent_table_error(self):
        """Test error when querying non-existent tables"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        nonexistent_queries = [
            "SELECT * FROM nonexistent_table",
            "SELECT COUNT(*) FROM missing_table",
            "SELECT * FROM table_that_does_not_exist WHERE id = 1",
        ]
        
        for query in nonexistent_queries:
            with pytest.raises(Exception):
                engine.execute_query_sync(query)
    
    def test_nonexistent_column_error(self):
        """Test error when referencing non-existent columns"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("column_test", 100)
        
        # Test data has columns: id, value, category
        invalid_column_queries = [
            "SELECT nonexistent_column FROM column_test",
            "SELECT * FROM column_test WHERE missing_column = 1",
            "SELECT * FROM column_test ORDER BY invalid_column",
            "SELECT COUNT(*) FROM column_test GROUP BY unknown_column",
        ]
        
        for query in invalid_column_queries:
            with pytest.raises(Exception):
                engine.execute_query_sync(query)
    
    def test_type_mismatch_errors(self):
        """Test handling of type mismatches in queries"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("type_test", 100)
        
        # These should cause type-related errors
        type_error_queries = [
            "SELECT * FROM type_test WHERE category > 100",  # string vs number
            "SELECT id + category FROM type_test",  # number + string
        ]
        
        for query in type_error_queries:
            with pytest.raises(Exception):
                engine.execute_query_sync(query)
    
    def test_aggregation_errors(self):
        """Test errors in aggregation queries"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("agg_error_test", 100)
        
        aggregation_error_queries = [
            "SELECT id, COUNT(*) FROM agg_error_test",  # non-grouped column in GROUP BY query
            "SELECT * FROM agg_error_test HAVING COUNT(*) > 10",  # HAVING without GROUP BY
        ]
        
        for query in aggregation_error_queries:
            with pytest.raises(Exception):
                engine.execute_query_sync(query)


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestEngineStateErrors:
    """Test error handling related to engine state and operations"""
    
    def test_query_validation_edge_cases(self):
        """Test query validation with edge cases"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        # Valid queries should return True
        assert engine.validate_query_sync("SELECT 1") == True
        assert engine.validate_query_sync("SELECT 1 + 1 as result") == True
        
        # Invalid queries should return False (not raise exceptions)
        assert engine.validate_query_sync("INVALID SQL") == False
        assert engine.validate_query_sync("") == False
        assert engine.validate_query_sync("   ") == False
        assert engine.validate_query_sync("SELECT * FORM table") == False
    
    def test_empty_table_operations(self):
        """Test operations on empty tables"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        # Create an empty table by filtering all rows
        engine.register_test_data("empty_source", 100)
        
        # These should work but return empty results
        empty_result_queries = [
            "SELECT * FROM empty_source WHERE value > 10000",  # impossible condition
            "SELECT * FROM empty_source LIMIT 0",  # explicit empty limit
        ]
        
        for query in empty_result_queries:
            result = engine.execute_query_sync(query)
            assert result.rows == 0
            assert len(result.data) == 0
            assert result.execution_time_ms >= 0
    
    def test_very_large_limits(self):
        """Test behavior with very large LIMIT values"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("limit_test", 1000)
        
        # Large limit that exceeds available data
        result = engine.execute_query_sync("SELECT * FROM limit_test LIMIT 999999")
        assert result.rows == 1000  # Should return all available rows
        assert len(result.data) == 1000
    
    def test_table_name_edge_cases(self):
        """Test table registration with edge case names"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        # Valid table names that might cause issues
        valid_edge_cases = [
            "test_table_123",
            "table_with_underscores",
            "t",  # single character
        ]
        
        for table_name in valid_edge_cases:
            engine.register_test_data(table_name, 10)
            result = engine.execute_query_sync(f"SELECT COUNT(*) FROM {table_name}")
            assert result.rows == 1


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestConcurrencyErrors:
    """Test error handling under concurrent access"""
    
    def test_concurrent_query_errors(self):
        """Test that errors in one thread don't affect others"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("concurrent_error_test", 1000)
        
        def run_query(query_type):
            try:
                if query_type == "valid":
                    result = engine.execute_query_sync("SELECT COUNT(*) FROM concurrent_error_test")
                    return ("success", result.rows)
                else:  # invalid
                    engine.execute_query_sync("SELECT * FROM nonexistent_table")
                    return ("unexpected_success", None)
            except Exception as e:
                return ("error", str(e))
        
        # Mix of valid and invalid queries
        query_types = ["valid", "invalid", "valid", "invalid", "valid"]
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_query, qt) for qt in query_types]
            results = [future.result() for future in futures]
        
        # Valid queries should succeed, invalid should fail
        valid_results = [r for r in results if r[0] == "success"]
        error_results = [r for r in results if r[0] == "error"]
        
        assert len(valid_results) == 3  # 3 valid queries
        assert len(error_results) == 2  # 2 invalid queries
        
        # All valid queries should return the same count
        assert all(r[1] == 1000 for r in valid_results)
    
    def test_concurrent_table_registration(self):
        """Test concurrent table registration doesn't cause issues"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        def register_and_query(table_id):
            try:
                table_name = f"concurrent_table_{table_id}"
                engine.register_test_data(table_name, 100)
                result = engine.execute_query_sync(f"SELECT COUNT(*) FROM {table_name}")
                return ("success", result.rows)
            except Exception as e:
                return ("error", str(e))
        
        # Register multiple tables concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register_and_query, i) for i in range(10)]
            results = [future.result() for future in futures]
        
        # All operations should succeed
        successful_results = [r for r in results if r[0] == "success"]
        assert len(successful_results) == 10
        
        # All should return the expected count
        assert all(r[1] == 1 for r in successful_results)


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestResourceErrors:
    """Test error handling related to resource constraints"""
    
    def test_very_complex_query_handling(self):
        """Test handling of extremely complex queries"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("complex_test", 1000)
        
        # Intentionally complex query that might stress the system
        complex_query = """
        SELECT 
            category,
            COUNT(*) as count,
            AVG(value) as avg_val,
            SUM(value) as sum_val,
            MIN(value) as min_val,
            MAX(value) as max_val,
            SUM(CASE WHEN value > 500 THEN 1 ELSE 0 END) as high_count,
            SUM(CASE WHEN value < 250 THEN 1 ELSE 0 END) as low_count,
            AVG(CASE WHEN value > 750 THEN value ELSE NULL END) as high_avg
        FROM complex_test 
        GROUP BY category 
        HAVING COUNT(*) > 10
        ORDER BY avg_val DESC, count ASC
        """
        
        # Should handle complex query without crashing
        result = engine.execute_query_sync(complex_query)
        assert result.rows >= 0  # May be 0 if no groups meet HAVING condition
        assert result.execution_time_ms >= 0
        assert result.memory_used_bytes >= 0
    
    def test_query_timeout_behavior(self):
        """Test behavior with potentially long-running queries"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("timeout_test", 10_000)
        
        # Query that might take a while (full table scan with computation)
        potentially_slow_query = """
        SELECT 
            *,
            value * 2 as doubled,
            value * value as squared,
            CASE 
                WHEN value < 100 THEN 'low'
                WHEN value < 500 THEN 'medium'
                ELSE 'high'
            END as value_category
        FROM timeout_test 
        ORDER BY value DESC
        """
        
        start_time = time.time()
        result = engine.execute_query_sync(potentially_slow_query)
        execution_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 10 seconds)
        assert execution_time < 10.0, f"Query took too long: {execution_time:.2f}s"
        assert result.rows == 10_000
    
    def test_error_message_quality(self):
        """Test that error messages are informative"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        error_scenarios = [
            ("SELECT * FROM missing_table", ["missing_table", "table", "not found"]),
            ("SELECT invalid_column FROM test", ["invalid_column", "column"]),
            ("SELECT * FORM test", ["syntax", "FORM"]),
        ]
        
        for query, expected_keywords in error_scenarios:
            try:
                engine.execute_query_sync(query)
                pytest.fail(f"Expected error for query: {query}")
            except Exception as e:
                error_message = str(e).lower()
                
                # Error message should contain relevant keywords
                keyword_found = any(keyword.lower() in error_message for keyword in expected_keywords)
                assert keyword_found, f"Error message '{error_message}' lacks expected keywords {expected_keywords}"


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestEdgeCases:
    """Test various edge cases and boundary conditions"""
    
    def test_null_value_handling(self):
        """Test handling of NULL values in queries"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("null_test", 100)
        
        # Queries that might involve NULL handling
        null_queries = [
            "SELECT COUNT(*) FROM null_test",
            "SELECT AVG(value) FROM null_test",
            "SELECT category FROM null_test WHERE category IS NOT NULL",
        ]
        
        for query in null_queries:
            result = engine.execute_query_sync(query)
            assert result.rows >= 0
            assert result.execution_time_ms >= 0
    
    def test_special_character_handling(self):
        """Test handling of special characters in SQL"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("special_test", 100)
        
        # Queries with special characters and escape sequences
        special_queries = [
            "SELECT 'hello world' as greeting",
            "SELECT 'don\\'t' as contraction",
            "SELECT 'line1\\nline2' as multiline",
        ]
        
        for query in special_queries:
            result = engine.execute_query_sync(query)
            assert result.rows >= 0
    
    def test_boundary_value_queries(self):
        """Test queries with boundary values"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("boundary_test", 1000)
        
        boundary_queries = [
            "SELECT * FROM boundary_test WHERE value = 0",
            "SELECT * FROM boundary_test WHERE value = 1000",
            "SELECT * FROM boundary_test WHERE value < 0",
            "SELECT * FROM boundary_test WHERE value > 1000",
            "SELECT * FROM boundary_test LIMIT 0",
            "SELECT * FROM boundary_test LIMIT 1",
        ]
        
        for query in boundary_queries:
            result = engine.execute_query_sync(query)
            assert result.rows >= 0
            assert len(result.data) == result.rows


if __name__ == "__main__":
    if RUST_ENGINE_AVAILABLE:
        print("🛡️ Running error handling tests...")
        pytest.main([__file__, "-v"])
    else:
        print("❌ Rust engine not available - cannot run error handling tests")
        print("Build the engine with: cd bigquery-lite-engine && maturin develop --release")
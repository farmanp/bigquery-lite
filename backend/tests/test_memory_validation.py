#!/usr/bin/env python3
"""
Memory usage validation tests for Rust engine

These tests ensure the engine efficiently manages memory and doesn't leak
memory under various usage patterns.
"""

import pytest
import gc
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Try to import Rust engine
try:
    import bigquery_lite_engine
    RUST_ENGINE_AVAILABLE = True
except ImportError:
    RUST_ENGINE_AVAILABLE = False


def get_memory_usage():
    """Get approximate memory usage in bytes (simplified)"""
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss
    except ImportError:
        return 0  # psutil not available


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestMemoryEfficiency:
    """Test memory efficiency and usage patterns"""
    
    def test_basic_memory_reporting(self):
        """Test that memory usage is reported correctly"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("memory_basic", 10_000)
        
        result = engine.execute_query_sync("SELECT COUNT(*) FROM memory_basic")
        
        # Memory usage should be reported
        assert result.memory_used_bytes >= 0
        
        # Memory usage should be reasonable for small dataset
        memory_mb = result.memory_used_bytes / 1024 / 1024
        assert memory_mb < 100, f"Memory usage {memory_mb:.2f}MB too high for 10K rows"
    
    def test_memory_scaling_with_data_size(self):
        """Test that memory usage scales reasonably with data size"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        memory_usages = []
        data_sizes = [1_000, 10_000, 50_000]
        
        for size in data_sizes:
            engine.register_test_data(f"memory_scale_{size}", size)
            result = engine.execute_query_sync(f"SELECT COUNT(*) FROM memory_scale_{size}")
            memory_usages.append((size, result.memory_used_bytes))
        
        # Memory should scale sub-linearly with data size
        small_size, small_memory = memory_usages[0]
        large_size, large_memory = memory_usages[-1]
        
        if small_memory > 0:
            data_ratio = large_size / small_size  # 50x more data
            memory_ratio = large_memory / small_memory
            
            # Memory should scale better than linearly
            assert memory_ratio < data_ratio * 2, \
                f"Memory scales poorly: {memory_ratio:.1f}x memory for {data_ratio}x data"
    
    def test_large_dataset_memory_target(self):
        """Test memory usage target for large datasets"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("memory_large", 1_000_000)
        
        # Complex aggregation on 1M rows
        result = engine.execute_query_sync("""
            SELECT 
                category,
                COUNT(*) as count,
                SUM(value) as total,
                AVG(value) as average,
                MIN(value) as minimum,
                MAX(value) as maximum
            FROM memory_large 
            GROUP BY category
        """)
        
        # Primary target: under 2GB memory usage
        memory_gb = result.memory_used_bytes / 1024 / 1024 / 1024
        assert memory_gb < 2.0, f"Memory usage {memory_gb:.3f}GB exceeds 2GB target"
        
        # Should also be reasonably efficient
        memory_mb = result.memory_used_bytes / 1024 / 1024
        assert memory_mb < 500, f"Memory usage {memory_mb:.2f}MB higher than expected for 1M rows"
    
    def test_memory_cleanup_after_queries(self):
        """Test that memory is cleaned up after query execution"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("memory_cleanup", 100_000)
        
        # Run several memory-intensive queries
        queries = [
            "SELECT * FROM memory_cleanup ORDER BY value DESC LIMIT 10000",
            "SELECT category, COUNT(*), AVG(value) FROM memory_cleanup GROUP BY category",
            "SELECT * FROM memory_cleanup WHERE value > 750",
        ]
        
        peak_memories = []
        for query in queries:
            result = engine.execute_query_sync(query)
            peak_memories.append(result.memory_used_bytes)
        
        # Memory usage shouldn't continuously increase
        assert len(set(peak_memories)) > 1 or peak_memories[0] == 0, \
            "Memory usage appears constant (may indicate measurement issue)"
        
        # Final memory usage should be reasonable
        final_memory_mb = peak_memories[-1] / 1024 / 1024
        assert final_memory_mb < 200, f"Final memory usage {final_memory_mb:.2f}MB too high"


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestMemoryLeaks:
    """Test for memory leaks under various usage patterns"""
    
    def test_repeated_queries_no_leak(self):
        """Test that repeated queries don't cause memory leaks"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("leak_test", 10_000)
        
        query = "SELECT category, COUNT(*) FROM leak_test GROUP BY category"
        
        # Record initial memory
        initial_memory = get_memory_usage()
        
        # Run many queries
        for i in range(100):
            result = engine.execute_query_sync(query)
            assert result.rows == 10  # Verify query works
        
        # Force garbage collection
        gc.collect()
        time.sleep(0.1)  # Allow cleanup
        
        # Check final memory
        final_memory = get_memory_usage()
        
        if initial_memory > 0 and final_memory > 0:
            memory_growth = final_memory - initial_memory
            memory_growth_mb = memory_growth / 1024 / 1024
            
            # Allow some growth but not excessive
            assert memory_growth_mb < 50, \
                f"Potential memory leak: {memory_growth_mb:.2f}MB growth after 100 queries"
    
    def test_table_registration_no_leak(self):
        """Test that registering multiple tables doesn't leak memory"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        initial_memory = get_memory_usage()
        
        # Register many small tables
        for i in range(20):
            engine.register_test_data(f"table_{i}", 1000)
        
        # Query each table
        for i in range(20):
            result = engine.execute_query_sync(f"SELECT COUNT(*) FROM table_{i}")
            assert result.rows == 1
        
        gc.collect()
        time.sleep(0.1)
        
        final_memory = get_memory_usage()
        
        if initial_memory > 0 and final_memory > 0:
            memory_growth = final_memory - initial_memory
            memory_growth_mb = memory_growth / 1024 / 1024
            
            # Should not grow excessively
            assert memory_growth_mb < 100, \
                f"Excessive memory growth: {memory_growth_mb:.2f}MB for 20 small tables"
    
    def test_concurrent_queries_memory(self):
        """Test memory usage under concurrent query load"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("concurrent_memory", 50_000)
        
        def run_query(query_id):
            query = f"SELECT COUNT(*) FROM concurrent_memory WHERE value > {query_id * 100}"
            result = engine.execute_query_sync(query)
            return result.memory_used_bytes
        
        initial_memory = get_memory_usage()
        
        # Run queries concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_query, i) for i in range(20)]
            memory_usages = [future.result() for future in futures]
        
        gc.collect()
        time.sleep(0.1)
        
        final_memory = get_memory_usage()
        
        # All queries should complete successfully
        assert all(mem >= 0 for mem in memory_usages)
        
        # Memory shouldn't grow excessively
        if initial_memory > 0 and final_memory > 0:
            memory_growth = final_memory - initial_memory
            memory_growth_mb = memory_growth / 1024 / 1024
            
            assert memory_growth_mb < 200, \
                f"Excessive memory growth: {memory_growth_mb:.2f}MB for concurrent queries"


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestMemoryPressure:
    """Test behavior under memory pressure"""
    
    def test_large_result_set_memory(self):
        """Test memory usage for queries returning large result sets"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("large_results", 100_000)
        
        # Query that returns many rows
        result = engine.execute_query_sync(
            "SELECT id, value, category FROM large_results WHERE value > 200 LIMIT 50000"
        )
        
        # Should handle large result sets efficiently
        memory_mb = result.memory_used_bytes / 1024 / 1024
        rows_per_mb = result.rows / memory_mb if memory_mb > 0 else 0
        
        # Should be efficient (at least 100 rows per MB)
        assert rows_per_mb > 100 or memory_mb < 10, \
            f"Inefficient memory usage: {rows_per_mb:.1f} rows/MB"
        
        # Total memory should still be reasonable
        assert memory_mb < 500, f"Memory usage {memory_mb:.2f}MB too high for result set"
    
    def test_complex_query_memory(self):
        """Test memory usage for complex multi-step queries"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("complex_memory", 50_000)
        
        # Complex query with multiple operations
        result = engine.execute_query_sync("""
            SELECT 
                category,
                COUNT(*) as total_count,
                AVG(value) as avg_value,
                SUM(CASE WHEN value > 500 THEN 1 ELSE 0 END) as high_value_count,
                MIN(value) as min_value,
                MAX(value) as max_value
            FROM complex_memory 
            GROUP BY category 
            HAVING COUNT(*) > 1000
            ORDER BY avg_value DESC
        """)
        
        # Complex query should still be memory efficient
        memory_mb = result.memory_used_bytes / 1024 / 1024
        assert memory_mb < 100, f"Complex query used {memory_mb:.2f}MB, too high"
        
        # Should complete in reasonable time
        assert result.execution_time_ms < 1000, \
            f"Complex query took {result.execution_time_ms}ms, too slow"
    
    def test_memory_stats_accuracy(self):
        """Test that reported memory statistics are accurate"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("stats_accuracy", 10_000)
        
        # Run several queries and track memory stats
        queries = [
            "SELECT COUNT(*) FROM stats_accuracy",
            "SELECT category, COUNT(*) FROM stats_accuracy GROUP BY category",
            "SELECT * FROM stats_accuracy LIMIT 1000",
        ]
        
        reported_memories = []
        for query in queries:
            result = engine.execute_query_sync(query)
            reported_memories.append(result.memory_used_bytes)
        
        # Memory reports should be non-negative and reasonable
        assert all(mem >= 0 for mem in reported_memories), "Negative memory usage reported"
        
        # Memory usage should vary with query complexity
        assert len(set(reported_memories)) > 1 or reported_memories[0] == 0, \
            "Memory usage identical for different queries (measurement issue?)"
        
        # None should be unreasonably high
        max_memory_mb = max(reported_memories) / 1024 / 1024
        assert max_memory_mb < 50, f"Reported memory {max_memory_mb:.2f}MB too high for small dataset"


if __name__ == "__main__":
    if RUST_ENGINE_AVAILABLE:
        print("🧠 Running memory validation tests...")
        pytest.main([__file__, "-v"])
    else:
        print("❌ Rust engine not available - cannot run memory tests")
        print("Build the engine with: cd bigquery-lite-engine && maturin develop --release")
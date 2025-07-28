#!/usr/bin/env python3
"""
Performance benchmark and regression tests for Rust engine

These tests validate that the Rust engine meets performance targets and
doesn't regress over time.
"""

import pytest
import time
import statistics
import asyncio
from typing import List, Dict, Any

from runners.duckdb_runner import DuckDBRunner

# Try to import Rust engine
try:
    import bigquery_lite_engine
    RUST_ENGINE_AVAILABLE = True
except ImportError:
    RUST_ENGINE_AVAILABLE = False


class PerformanceBenchmark:
    """Helper class for running performance benchmarks"""
    
    @staticmethod
    async def benchmark_python_engine(queries: List[str], data_size: int) -> List[Dict[str, Any]]:
        """Benchmark Python DuckDB engine"""
        runner = DuckDBRunner()
        await runner.initialize()
        
        # Create test data
        await runner.execute_query(f"""
            CREATE TABLE perf_test AS 
            SELECT 
                row_number() OVER () as id,
                random() * 1000 as value,
                'category_' || (random() * 10)::int as category
            FROM range({data_size})
        """)
        
        results = []
        for query in queries:
            start_time = time.time()
            result = await runner.execute_query(query.replace("test_data", "perf_test"))
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            results.append({
                "query": query,
                "execution_time_ms": execution_time,
                "rows": result.get("rows", 0),
                "engine": "python_duckdb"
            })
        
        await runner.cleanup()
        return results
    
    @staticmethod
    def benchmark_rust_engine(queries: List[str], data_size: int) -> List[Dict[str, Any]]:
        """Benchmark Rust DataFusion engine"""
        if not RUST_ENGINE_AVAILABLE:
            return []
        
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("test_data", data_size)
        
        results = []
        for query in queries:
            start_time = time.time()
            result = engine.execute_query_sync(query)
            total_time = (time.time() - start_time) * 1000  # Convert to ms
            
            results.append({
                "query": query,
                "execution_time_ms": result.execution_time_ms,
                "total_time_ms": total_time,
                "rows": result.rows,
                "memory_used_mb": result.memory_used_bytes / 1024 / 1024,
                "engine": "rust_blaze"
            })
        
        return results


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestPerformanceTargets:
    """Test that the Rust engine meets specific performance targets"""
    
    def test_small_dataset_speed_target(self):
        """Test performance target for small datasets (1K rows)"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("small_target", 1_000)
        
        # Simple aggregation should be very fast
        result = engine.execute_query_sync("SELECT COUNT(*) FROM small_target")
        assert result.execution_time_ms < 10  # Less than 10ms
        
        # GROUP BY should also be fast
        result = engine.execute_query_sync(
            "SELECT category, COUNT(*) FROM small_target GROUP BY category"
        )
        assert result.execution_time_ms < 50  # Less than 50ms
    
    def test_medium_dataset_speed_target(self):
        """Test performance target for medium datasets (100K rows)"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("medium_target", 100_000)
        
        # Complex aggregation should be reasonably fast
        result = engine.execute_query_sync("""
            SELECT 
                category, 
                COUNT(*) as count,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value
            FROM medium_target 
            GROUP BY category 
            ORDER BY count DESC
        """)
        
        assert result.execution_time_ms < 100  # Less than 100ms
        assert result.rows == 10  # Should have 10 categories
    
    def test_large_dataset_speed_target(self):
        """Test performance target for large datasets (1M rows) - THE KEY TEST"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("large_target", 1_000_000)
        
        # This is the primary target: 1M+ row aggregations in <100ms
        result = engine.execute_query_sync("""
            SELECT 
                category, 
                COUNT(*) as count,
                SUM(value) as total_value,
                AVG(value) as avg_value
            FROM large_target 
            GROUP BY category
        """)
        
        # PRIMARY TARGET: Must complete in under 100ms
        assert result.execution_time_ms < 100, f"Failed target: {result.execution_time_ms}ms >= 100ms"
        assert result.rows == 10  # Should have 10 categories
        
        # Memory efficiency target: under 2GB
        memory_gb = result.memory_used_bytes / 1024 / 1024 / 1024
        assert memory_gb < 2.0, f"Memory usage {memory_gb:.3f}GB exceeds 2GB target"
    
    def test_memory_efficiency_target(self):
        """Test memory efficiency targets"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("memory_target", 500_000)
        
        # Multiple complex queries to test memory management
        queries = [
            "SELECT COUNT(*) FROM memory_target",
            "SELECT category, COUNT(*), AVG(value) FROM memory_target GROUP BY category",
            "SELECT * FROM memory_target WHERE value > 750 ORDER BY value DESC LIMIT 100",
            "SELECT category, MIN(value), MAX(value), SUM(value) FROM memory_target GROUP BY category",
        ]
        
        max_memory = 0
        for query in queries:
            result = engine.execute_query_sync(query)
            max_memory = max(max_memory, result.memory_used_bytes)
        
        # Memory usage should stay reasonable
        memory_mb = max_memory / 1024 / 1024
        assert memory_mb < 500, f"Memory usage {memory_mb:.2f}MB too high for 500K rows"


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestPerformanceRegression:
    """Test for performance regressions over time"""
    
    def test_execution_time_consistency(self):
        """Test that execution times are consistent across multiple runs"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("consistency_test", 50_000)
        
        query = "SELECT category, COUNT(*), AVG(value) FROM consistency_test GROUP BY category"
        
        # Run the same query multiple times
        times = []
        for _ in range(10):
            result = engine.execute_query_sync(query)
            times.append(result.execution_time_ms)
        
        # Check consistency (coefficient of variation should be low)
        mean_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        cv = std_dev / mean_time if mean_time > 0 else 0
        
        # Coefficient of variation should be less than 50% (reasonable for timing)
        assert cv < 0.5, f"Execution times too variable: CV={cv:.2f}, times={times}"
        assert mean_time < 100, f"Mean execution time {mean_time:.2f}ms too slow"
    
    def test_memory_usage_consistency(self):
        """Test that memory usage is consistent across runs"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("memory_consistency", 100_000)
        
        query = "SELECT category, COUNT(*), SUM(value) FROM memory_consistency GROUP BY category"
        
        memory_usages = []
        for _ in range(5):
            result = engine.execute_query_sync(query)
            memory_usages.append(result.memory_used_bytes)
        
        # Memory usage should be relatively consistent
        max_memory = max(memory_usages)
        min_memory = min(memory_usages)
        
        if max_memory > 0:
            variation = (max_memory - min_memory) / max_memory
            assert variation < 0.2, f"Memory usage too variable: {memory_usages}"
    
    def test_performance_scaling(self):
        """Test that performance scales reasonably with data size"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        
        sizes_and_times = []
        query = "SELECT category, COUNT(*) FROM scaling_test GROUP BY category"
        
        # Test different data sizes
        for size in [1_000, 10_000, 100_000]:
            engine.register_test_data("scaling_test", size)
            
            result = engine.execute_query_sync(query)
            sizes_and_times.append((size, result.execution_time_ms))
        
        # Performance should scale sub-linearly (better than O(n))
        small_time = sizes_and_times[0][1]  # 1K rows
        large_time = sizes_and_times[2][1]  # 100K rows
        
        # 100x more data should take less than 100x more time
        if small_time > 0:
            scaling_factor = large_time / small_time
            data_scaling = 100  # 100K / 1K
            
            assert scaling_factor < data_scaling, \
                f"Performance scales poorly: {scaling_factor:.1f}x time for {data_scaling}x data"


@pytest.mark.asyncio
@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestComparativeBenchmarks:
    """Compare Rust engine performance against Python baseline"""
    
    async def test_speedup_validation_small(self):
        """Validate speedup for small datasets"""
        queries = [
            "SELECT COUNT(*) FROM test_data",
            "SELECT category, COUNT(*) FROM test_data GROUP BY category",
        ]
        
        data_size = 10_000
        
        # Benchmark both engines
        python_results = await PerformanceBenchmark.benchmark_python_engine(queries, data_size)
        rust_results = PerformanceBenchmark.benchmark_rust_engine(queries, data_size)
        
        assert len(rust_results) == len(python_results)
        
        # Calculate speedups
        speedups = []
        for py_result, rust_result in zip(python_results, rust_results):
            if rust_result["execution_time_ms"] > 0:
                speedup = py_result["execution_time_ms"] / rust_result["execution_time_ms"]
                speedups.append(speedup)
        
        # Should see some speedup even for small datasets
        avg_speedup = statistics.mean(speedups) if speedups else 0
        assert avg_speedup > 1.0, f"No speedup observed: {avg_speedup:.2f}x"
    
    async def test_speedup_validation_large(self):
        """Validate speedup for large datasets - target 10x improvement"""
        queries = [
            "SELECT COUNT(*) FROM test_data",
            "SELECT category, COUNT(*), AVG(value) FROM test_data GROUP BY category",
            "SELECT category, MIN(value), MAX(value) FROM test_data GROUP BY category",
        ]
        
        data_size = 100_000  # Use 100K for reasonable test time
        
        # Benchmark both engines
        python_results = await PerformanceBenchmark.benchmark_python_engine(queries, data_size)
        rust_results = PerformanceBenchmark.benchmark_rust_engine(queries, data_size)
        
        assert len(rust_results) == len(python_results)
        
        # Calculate overall speedup
        total_python_time = sum(r["execution_time_ms"] for r in python_results)
        total_rust_time = sum(r["execution_time_ms"] for r in rust_results)
        
        if total_rust_time > 0:
            overall_speedup = total_python_time / total_rust_time
            
            # Should see significant speedup (targeting 10x, accept 3x+ as good)
            assert overall_speedup > 3.0, f"Insufficient speedup: {overall_speedup:.2f}x"
            
            # If we hit 10x, that's excellent!
            if overall_speedup >= 10.0:
                print(f"🎯 EXCELLENT: Achieved {overall_speedup:.1f}x speedup (target: 10x)")
            else:
                print(f"✅ GOOD: Achieved {overall_speedup:.1f}x speedup (target: 10x)")


@pytest.mark.skipif(not RUST_ENGINE_AVAILABLE, reason="Rust engine not available")
class TestStressTests:
    """Stress tests to validate robustness under load"""
    
    def test_repeated_queries_stress(self):
        """Test engine stability under repeated query load"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("stress_test", 10_000)
        
        query = "SELECT category, COUNT(*), AVG(value) FROM stress_test GROUP BY category"
        
        # Run many queries to test for memory leaks or degradation
        execution_times = []
        for i in range(50):
            result = engine.execute_query_sync(query)
            execution_times.append(result.execution_time_ms)
            
            # Verify result consistency
            assert result.rows == 10
            assert result.execution_time_ms < 1000  # Should stay fast
        
        # Performance shouldn't degrade significantly over time
        early_times = execution_times[:10]
        late_times = execution_times[-10:]
        
        early_avg = statistics.mean(early_times)
        late_avg = statistics.mean(late_times)
        
        if early_avg > 0:
            degradation = late_avg / early_avg
            assert degradation < 2.0, f"Performance degraded {degradation:.1f}x over time"
    
    def test_large_result_set_handling(self):
        """Test handling of queries that return large result sets"""
        engine = bigquery_lite_engine.BlazeQueryEngine()
        engine.register_test_data("large_result", 50_000)
        
        # Query that returns many rows
        result = engine.execute_query_sync(
            "SELECT * FROM large_result WHERE value > 100 ORDER BY value LIMIT 5000"
        )
        
        assert result.rows <= 5000
        assert len(result.data) == result.rows
        assert result.execution_time_ms < 2000  # Should complete in reasonable time
        
        # Memory usage should be reasonable even for large results
        memory_mb = result.memory_used_bytes / 1024 / 1024
        assert memory_mb < 1000, f"Memory usage {memory_mb:.2f}MB too high for large result"


if __name__ == "__main__":
    if RUST_ENGINE_AVAILABLE:
        print("🚀 Running performance benchmarks...")
        pytest.main([__file__, "-v", "-s"])
    else:
        print("❌ Rust engine not available - cannot run benchmarks")
        print("Build the engine with: cd bigquery-lite-engine && maturin develop --release")
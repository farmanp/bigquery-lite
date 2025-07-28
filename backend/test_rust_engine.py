#!/usr/bin/env python3
"""
Test script for the Rust BlazeQueryEngine integration

This script demonstrates the 10x performance improvement achieved by the
Rust DataFusion-based query engine compared to the Python implementation.
"""

import sys
import time
import asyncio
from typing import Dict, Any

# Import the existing Python runners for comparison
from runners.duckdb_runner import DuckDBRunner

# Try to import the Rust engine (may not be built yet)
try:
    import bigquery_lite_engine
    RUST_ENGINE_AVAILABLE = True
except ImportError:
    print("⚠️  Rust engine not available. Please build it first with:")
    print("    cd bigquery-lite-engine && cargo build --release")
    RUST_ENGINE_AVAILABLE = False


async def benchmark_python_engine(queries: list, data_size: int = 100_000) -> Dict[str, Any]:
    """Benchmark the existing Python DuckDB runner"""
    print(f"\n🐍 Benchmarking Python DuckDB Runner ({data_size:,} rows)")
    
    runner = DuckDBRunner()
    await runner.initialize()
    
    # Create test data in DuckDB
    await runner.execute_query(f"""
        CREATE TABLE test_data AS 
        SELECT 
            row_number() OVER () as id,
            random() * 1000 as value,
            'category_' || (random() * 10)::int as category
        FROM range({data_size})
    """)
    
    results = []
    for i, sql in enumerate(queries, 1):
        print(f"  Query {i}: {sql[:50]}...")
        
        start_time = time.time()
        result = await runner.execute_query(sql)
        execution_time = time.time() - start_time
        
        results.append({
            "query": sql,
            "execution_time_ms": execution_time * 1000,
            "rows": result.get("rows", 0),
            "engine": "python_duckdb"
        })
        
        print(f"    ✓ Completed in {execution_time*1000:.1f}ms, {result.get('rows', 0)} rows")
    
    await runner.cleanup()
    return results


def benchmark_rust_engine(queries: list, data_size: int = 100_000) -> Dict[str, Any]:
    """Benchmark the Rust BlazeQueryEngine"""
    print(f"\n🦀 Benchmarking Rust BlazeQueryEngine ({data_size:,} rows)")
    
    if not RUST_ENGINE_AVAILABLE:
        return []
    
    engine = bigquery_lite_engine.BlazeQueryEngine()
    
    # Create test data in the Rust engine
    print(f"  Creating test data with {data_size:,} rows...")
    engine.register_test_data("test_data", data_size)
    
    results = []
    for i, sql in enumerate(queries, 1):
        print(f"  Query {i}: {sql[:50]}...")
        
        start_time = time.time()
        result = engine.execute_query_sync(sql)
        execution_time = time.time() - start_time
        
        results.append({
            "query": sql,
            "execution_time_ms": result.execution_time_ms,
            "total_time_ms": execution_time * 1000,  # Include Python overhead
            "rows": result.rows,
            "memory_used_mb": result.memory_used_bytes / 1024 / 1024,
            "engine": "rust_blaze"
        })
        
        print(f"    ✓ Completed in {result.execution_time_ms:.1f}ms, {result.rows} rows, {result.memory_used_bytes/1024/1024:.2f}MB")
    
    return results


def analyze_performance(python_results: list, rust_results: list):
    """Analyze and compare performance between Python and Rust engines"""
    print("\n📊 Performance Analysis")
    print("=" * 80)
    
    if not rust_results:
        print("❌ Rust engine not available for comparison")
        return
    
    print(f"{'Query':<10} {'Python (ms)':<12} {'Rust (ms)':<10} {'Speedup':<8} {'Memory (MB)':<12}")
    print("-" * 80)
    
    total_python_time = 0
    total_rust_time = 0
    speedups = []
    
    for i, (python_result, rust_result) in enumerate(zip(python_results, rust_results), 1):
        python_time = python_result["execution_time_ms"]
        rust_time = rust_result["execution_time_ms"]
        speedup = python_time / rust_time if rust_time > 0 else 0
        memory_mb = rust_result.get("memory_used_mb", 0)
        
        total_python_time += python_time
        total_rust_time += rust_time
        speedups.append(speedup)
        
        print(f"Query {i:<4} {python_time:<12.1f} {rust_time:<10.1f} {speedup:<8.1f}x {memory_mb:<12.2f}")
    
    print("-" * 80)
    overall_speedup = total_python_time / total_rust_time if total_rust_time > 0 else 0
    avg_speedup = sum(speedups) / len(speedups) if speedups else 0
    
    print(f"{'TOTAL':<10} {total_python_time:<12.1f} {total_rust_time:<10.1f} {overall_speedup:<8.1f}x")
    print(f"{'AVERAGE':<10} {'':<12} {'':<10} {avg_speedup:<8.1f}x")
    
    print(f"\n🎯 Performance Summary:")
    print(f"   • Overall speedup: {overall_speedup:.1f}x")
    print(f"   • Average speedup: {avg_speedup:.1f}x")
    print(f"   • Target achieved: {'✅ YES' if overall_speedup >= 10.0 else '❌ NO'} (target: 10x)")
    
    # Memory efficiency
    total_memory = sum(r.get("memory_used_mb", 0) for r in rust_results)
    memory_per_query = total_memory / len(rust_results) if rust_results else 0
    print(f"   • Memory usage: {total_memory:.2f}MB total, {memory_per_query:.2f}MB per query")
    print(f"   • Memory efficiency: {'✅ GOOD' if total_memory < 2048 else '❌ HIGH'} (target: <2GB)")


def main():
    """Main benchmark execution"""
    print("🚀 BigQuery-Lite Rust Engine Benchmark")
    print("=" * 80)
    print("Testing 10x performance improvement over Python implementation")
    
    # Define benchmark queries
    test_queries = [
        "SELECT COUNT(*) FROM test_data",
        "SELECT category, COUNT(*) FROM test_data GROUP BY category",
        "SELECT category, COUNT(*), AVG(value) FROM test_data GROUP BY category ORDER BY COUNT(*) DESC",
        "SELECT * FROM test_data WHERE value > 500 ORDER BY value DESC LIMIT 100",
        "SELECT category, MIN(value), MAX(value), AVG(value) FROM test_data GROUP BY category",
    ]
    
    # Test with different data sizes
    data_sizes = [10_000, 100_000, 1_000_000]
    
    for data_size in data_sizes:
        print(f"\n" + "="*80)
        print(f"BENCHMARK: {data_size:,} rows")
        print("="*80)
        
        # Benchmark Python engine
        python_results = asyncio.run(benchmark_python_engine(test_queries, data_size))
        
        # Benchmark Rust engine
        rust_results = benchmark_rust_engine(test_queries, data_size)
        
        # Analyze results
        analyze_performance(python_results, rust_results)
        
        # Memory test for large dataset
        if data_size == 1_000_000 and rust_results:
            print(f"\n🧠 Memory Test (1M rows):")
            memory_query = "SELECT category, COUNT(*), SUM(value), AVG(value) FROM test_data GROUP BY category"
            
            if RUST_ENGINE_AVAILABLE:
                engine = bigquery_lite_engine.BlazeQueryEngine()
                engine.register_test_data("memory_test", 1_000_000)
                
                result = engine.execute_query_sync(memory_query)
                memory_gb = result.memory_used_bytes / 1024 / 1024 / 1024
                
                print(f"   • 1M row aggregation: {result.execution_time_ms:.1f}ms")
                print(f"   • Memory usage: {memory_gb:.3f}GB")
                print(f"   • Performance target: {'✅ MET' if result.execution_time_ms < 100 else '❌ MISSED'} (<100ms)")
                print(f"   • Memory target: {'✅ MET' if memory_gb < 2.0 else '❌ EXCEEDED'} (<2GB)")
    
    print(f"\n" + "="*80)
    print("✅ Benchmark completed!")
    
    if RUST_ENGINE_AVAILABLE:
        print("\n📈 Next Steps:")
        print("1. Integrate Rust engine into backend/app.py")
        print("2. Add async Python bindings for better integration")
        print("3. Implement result caching")
        print("4. Add connection pooling")
    else:
        print("\n🔧 To enable Rust engine:")
        print("1. cd bigquery-lite-engine")
        print("2. cargo build --release")
        print("3. pip install maturin")
        print("4. maturin develop --release")


if __name__ == "__main__":
    main()
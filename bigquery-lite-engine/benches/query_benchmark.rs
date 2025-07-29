use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use tokio::runtime::Runtime;

use bigquery_lite_engine::{BlazeQueryEngine, BlazeResult};
use bigquery_lite_engine::benchmarks::{BenchmarkConfig, BenchmarkSuite};

/// Benchmark the Blaze query engine against various query types and data sizes
fn benchmark_query_engine(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    
    let mut group = c.benchmark_group("query_execution");
    
    // Test different data sizes
    let data_sizes = vec![10_000, 100_000, 1_000_000];
    
    for size in data_sizes {
        // Simple aggregation benchmark
        group.bench_with_input(
            BenchmarkId::new("simple_aggregation", size),
            &size,
            |b, &size| {
                b.to_async(&rt).iter(|| async {
                    let engine = BlazeQueryEngine::new().await.unwrap();
                    let batches = create_test_data(size).await.unwrap();
                    engine.register_table("test_data", batches).await.unwrap();
                    
                    let result = engine.execute_query(black_box(
                        "SELECT COUNT(*) FROM test_data"
                    )).await.unwrap();
                    
                    black_box(result)
                });
            },
        );
        
        // Group by aggregation benchmark
        group.bench_with_input(
            BenchmarkId::new("group_by_aggregation", size),
            &size,
            |b, &size| {
                b.to_async(&rt).iter(|| async {
                    let engine = BlazeQueryEngine::new().await.unwrap();
                    let batches = create_test_data(size).await.unwrap();
                    engine.register_table("test_data", batches).await.unwrap();
                    
                    let result = engine.execute_query(black_box(
                        "SELECT category, COUNT(*), AVG(value) FROM test_data GROUP BY category"
                    )).await.unwrap();
                    
                    black_box(result)
                });
            },
        );
        
        // Complex analytics benchmark
        if size <= 100_000 { // Limit complex queries to smaller datasets for CI
            group.bench_with_input(
                BenchmarkId::new("complex_analytics", size),
                &size,
                |b, &size| {
                    b.to_async(&rt).iter(|| async {
                        let engine = BlazeQueryEngine::new().await.unwrap();
                        let batches = create_test_data(size).await.unwrap();
                        engine.register_table("test_data", batches).await.unwrap();
                        
                        let result = engine.execute_query(black_box(
                            "SELECT category, SUM(amount), AVG(value), COUNT(*) 
                             FROM test_data 
                             WHERE flag = true 
                             GROUP BY category 
                             ORDER BY SUM(amount) DESC"
                        )).await.unwrap();
                        
                        black_box(result)
                    });
                },
            );
        }
    }
    
    group.finish();
}

/// Benchmark memory efficiency
fn benchmark_memory_usage(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    
    let mut group = c.benchmark_group("memory_efficiency");
    group.sample_size(10); // Fewer samples for memory tests
    
    group.bench_function("large_dataset_1m_rows", |b| {
        b.to_async(&rt).iter(|| async {
            let engine = BlazeQueryEngine::new().await.unwrap();
            let batches = create_test_data(1_000_000).await.unwrap();
            engine.register_table("large_data", batches).await.unwrap();
            
            let result = engine.execute_query(black_box(
                "SELECT COUNT(*), SUM(value), AVG(amount) FROM large_data"
            )).await.unwrap();
            
            // Verify memory usage is reasonable
            assert!(result.memory_used_bytes < 2 * 1024 * 1024 * 1024); // < 2GB
            
            black_box(result)
        });
    });
    
    group.finish();
}

/// Benchmark suite for comprehensive performance testing
fn benchmark_comprehensive_suite(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    
    c.bench_function("comprehensive_benchmark_suite", |b| {
        b.to_async(&rt).iter(|| async {
            let config = BenchmarkConfig {
                iterations: 3, // Reduced for benchmark speed
                dataset_sizes: vec![10_000, 100_000],
                ..Default::default()
            };
            
            let suite = BenchmarkSuite::new(config).await.unwrap();
            let results = suite.run_benchmarks().await.unwrap();
            
            // Verify performance requirements
            for result in &results {
                assert!(result.performance_metrics.avg_speedup > 1.0);
                assert!(result.performance_metrics.success_rate > 0.8);
            }
            
            black_box(results)
        });
    });
}

/// Create test data for benchmarks
async fn create_test_data(
    rows: usize
) -> BlazeResult<Vec<datafusion::arrow::record_batch::RecordBatch>> {
    use datafusion::arrow::array::*;
    use datafusion::arrow::datatypes::{Schema, Field, DataType};
    use std::sync::Arc;
    use rand::Rng;

    let mut rng = rand::thread_rng();
    
    let schema = Arc::new(Schema::new(vec![
        Field::new("id", DataType::Int64, false),
        Field::new("value", DataType::Float64, false),
        Field::new("category", DataType::Utf8, false),
        Field::new("amount", DataType::Decimal128(10, 2), false),
        Field::new("flag", DataType::Boolean, false),
    ]));

    let batch_size = 10_000;
    let mut batches = Vec::new();

    for batch_start in (0..rows).step_by(batch_size) {
        let batch_rows = std::cmp::min(batch_size, rows - batch_start);
        
        let id_array = Int64Array::from_iter_values(
            (batch_start..batch_start + batch_rows).map(|i| i as i64)
        );
        
        let value_array = Float64Array::from_iter_values(
            (0..batch_rows).map(|_| rng.gen_range(0.0..1000.0))
        );
        
        let category_array = StringArray::from_iter_values(
            (0..batch_rows).map(|i| format!("category_{}", (batch_start + i) % 10))
        );
        
        let amount_array = Decimal128Array::from_iter_values(
            (0..batch_rows).map(|_| rng.gen_range(100..10000))
        );
        
        let flag_array = BooleanArray::from_iter_values(
            (0..batch_rows).map(|_| rng.gen_bool(0.5))
        );

        let batch = datafusion::arrow::record_batch::RecordBatch::try_new(
            schema.clone(),
            vec![
                Arc::new(id_array),
                Arc::new(value_array),
                Arc::new(category_array),
                Arc::new(amount_array),
                Arc::new(flag_array),
            ],
        )?;

        batches.push(batch);
    }

    Ok(batches)
}

criterion_group!(
    benches,
    benchmark_query_engine,
    benchmark_memory_usage,
    benchmark_comprehensive_suite
);
criterion_main!(benches);
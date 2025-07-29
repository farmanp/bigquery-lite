use std::sync::Arc;
use tokio;

use bigquery_lite_engine::{BlazeQueryEngine, BlazeResult};

#[tokio::test]
async fn test_engine_creation() -> BlazeResult<()> {
    let engine = BlazeQueryEngine::new().await?;
    let stats = engine.get_stats().await;
    
    assert_eq!(stats.total_queries, 0);
    assert_eq!(stats.registered_tables, 0);
    assert_eq!(stats.avg_execution_time_ms, 0.0);
    
    Ok(())
}

#[tokio::test]
async fn test_basic_query_execution() -> BlazeResult<()> {
    let engine = BlazeQueryEngine::new().await?;
    
    // Create test data
    let test_data = create_simple_test_data().await?;
    engine.register_table("test_table", test_data).await?;
    
    // Execute simple query
    let result = engine.execute_query("SELECT COUNT(*) FROM test_table").await?;
    
    assert_eq!(result.rows, 1);
    assert!(result.execution_time_ms > 0);
    assert_eq!(result.engine, "blaze");
    assert!(!result.data.is_empty());
    
    Ok(())
}

#[tokio::test]
async fn test_aggregation_queries() -> BlazeResult<()> {
    let engine = BlazeQueryEngine::new().await?;
    
    // Create test data with multiple categories
    let test_data = create_categorized_test_data(1000).await?;
    engine.register_table("categories", test_data).await?;
    
    // Test GROUP BY query
    let result = engine.execute_query(
        "SELECT category, COUNT(*), AVG(value) FROM categories GROUP BY category ORDER BY category"
    ).await?;
    
    assert!(result.rows > 0);
    assert!(result.rows <= 10); // Should have categories 0-9
    assert!(result.execution_time_ms < 1000); // Should be fast
    
    // Verify data structure
    assert!(!result.data.is_empty());
    let first_row = &result.data[0];
    assert!(first_row.contains_key("category"));
    assert!(first_row.contains_key("COUNT(*)"));
    assert!(first_row.contains_key("AVG(categories.value)"));
    
    Ok(())
}

#[tokio::test]
async fn test_filtering_and_ordering() -> BlazeResult<()> {
    let engine = BlazeQueryEngine::new().await?;
    
    let test_data = create_categorized_test_data(1000).await?;
    engine.register_table("filtered", test_data).await?;
    
    // Test WHERE clause with ORDER BY and LIMIT
    let result = engine.execute_query(
        "SELECT * FROM filtered WHERE value > 500 ORDER BY value DESC LIMIT 10"
    ).await?;
    
    assert!(result.rows <= 10);
    assert!(result.rows > 0);
    
    // Verify ordering (values should be descending)
    if result.data.len() > 1 {
        let first_value = result.data[0]["value"].as_f64().unwrap();
        let second_value = result.data[1]["value"].as_f64().unwrap();
        assert!(first_value >= second_value);
    }
    
    Ok(())
}

#[tokio::test]
async fn test_table_management() -> BlazeResult<()> {
    let engine = BlazeQueryEngine::new().await?;
    
    // Initially no tables
    let tables = engine.list_tables().await?;
    assert!(tables.is_empty());
    
    // Register a table
    let test_data = create_simple_test_data().await?;
    engine.register_table("managed_table", test_data).await?;
    
    // Should now have one table
    let tables = engine.list_tables().await?;
    assert_eq!(tables.len(), 1);
    assert!(tables.contains(&"managed_table".to_string()));
    
    // Stats should reflect the registered table
    let stats = engine.get_stats().await;
    assert_eq!(stats.registered_tables, 1);
    
    Ok(())
}

#[tokio::test]
async fn test_query_validation() -> BlazeResult<()> {
    let engine = BlazeQueryEngine::new().await?;
    
    // Valid query should return true
    let is_valid = engine.validate_query("SELECT 1").await?;
    assert!(is_valid);
    
    // Invalid query should return false
    let is_invalid = engine.validate_query("INVALID SQL SYNTAX").await?;
    assert!(!is_invalid);
    
    Ok(())
}

#[tokio::test]
async fn test_performance_tracking() -> BlazeResult<()> {
    let engine = BlazeQueryEngine::new().await?;
    
    let test_data = create_simple_test_data().await?;
    engine.register_table("perf_test", test_data).await?;
    
    // Execute multiple queries
    for _ in 0..5 {
        engine.execute_query("SELECT COUNT(*) FROM perf_test").await?;
    }
    
    let stats = engine.get_stats().await;
    assert_eq!(stats.total_queries, 5);
    assert!(stats.avg_execution_time_ms > 0.0);
    
    Ok(())
}

#[tokio::test]
async fn test_memory_efficiency() -> BlazeResult<()> {
    let engine = BlazeQueryEngine::new().await?;
    
    // Create larger dataset
    let test_data = create_categorized_test_data(10_000).await?;
    engine.register_table("memory_test", test_data).await?;
    
    let result = engine.execute_query(
        "SELECT category, COUNT(*), AVG(value), SUM(value) FROM memory_test GROUP BY category"
    ).await?;
    
    // Memory usage should be reasonable
    assert!(result.memory_used_bytes < 100_000_000); // Less than 100MB
    assert!(result.execution_time_ms < 1000); // Less than 1 second
    
    Ok(())
}

#[tokio::test]
async fn test_concurrent_queries() -> BlazeResult<()> {
    let engine = Arc::new(BlazeQueryEngine::new().await?);
    
    let test_data = create_categorized_test_data(1000).await?;
    engine.register_table("concurrent_test", test_data).await?;
    
    // Execute multiple queries concurrently
    let mut handles = vec![];
    
    for i in 0..10 {
        let engine_clone = engine.clone();
        let handle = tokio::spawn(async move {
            engine_clone.execute_query(&format!(
                "SELECT COUNT(*) FROM concurrent_test WHERE value > {}", 
                i * 100
            )).await
        });
        handles.push(handle);
    }
    
    // Wait for all queries to complete
    for handle in handles {
        let result = handle.await.unwrap()?;
        assert!(result.rows > 0);
    }
    
    let stats = engine.get_stats().await;
    assert_eq!(stats.total_queries, 10);
    
    Ok(())
}

#[tokio::test]
async fn test_error_handling() -> BlazeResult<()> {
    let engine = BlazeQueryEngine::new().await?;
    
    // Query non-existent table should fail
    let result = engine.execute_query("SELECT * FROM non_existent_table").await;
    assert!(result.is_err());
    
    // Empty table registration should fail
    let empty_batches = vec![];
    let result = engine.register_table("empty", empty_batches).await;
    assert!(result.is_err());
    
    Ok(())
}

// Helper functions to create test data
async fn create_simple_test_data() -> BlazeResult<Vec<datafusion::arrow::record_batch::RecordBatch>> {
    use datafusion::arrow::array::*;
    use datafusion::arrow::datatypes::{Schema, Field, DataType};
    use std::sync::Arc;

    let schema = Arc::new(Schema::new(vec![
        Field::new("id", DataType::Int64, false),
        Field::new("value", DataType::Float64, false),
    ]));

    let id_array = Int64Array::from(vec![1, 2, 3, 4, 5]);
    let value_array = Float64Array::from(vec![10.0, 20.0, 30.0, 40.0, 50.0]);

    let batch = datafusion::arrow::record_batch::RecordBatch::try_new(
        schema,
        vec![Arc::new(id_array), Arc::new(value_array)],
    )?;

    Ok(vec![batch])
}

async fn create_categorized_test_data(
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
    ]));

    let batch_size = 1000;
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

        let batch = datafusion::arrow::record_batch::RecordBatch::try_new(
            schema.clone(),
            vec![
                Arc::new(id_array),
                Arc::new(value_array),
                Arc::new(category_array),
            ],
        )?;

        batches.push(batch);
    }

    Ok(batches)
}
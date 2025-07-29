//! Core BlazeQueryEngine implementation using DataFusion

use std::sync::Arc;
use std::collections::HashMap;
use std::time::Instant;

use datafusion::prelude::*;
use datafusion::execution::context::SessionConfig;
use datafusion::execution::runtime_env::RuntimeEnvBuilder;
use datafusion::datasource::MemTable;
use datafusion::arrow::record_batch::RecordBatch;
use datafusion::arrow::datatypes::Schema;
use datafusion::arrow::array::Array;
use datafusion::execution::memory_pool::{GreedyMemoryPool, MemoryPool};

use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use tracing::{info, warn, error, debug, instrument};

use crate::error::{BlazeError, BlazeResult};

/// Query execution result with performance metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResult {
    /// Number of rows returned
    pub rows: usize,
    /// Query execution time in milliseconds
    pub execution_time_ms: u64,
    /// Memory used during execution in bytes
    pub memory_used_bytes: u64,
    /// Query result data as JSON-serializable values
    pub data: Vec<HashMap<String, serde_json::Value>>,
    /// Query plan for debugging
    pub query_plan: Option<String>,
    /// Engine identifier
    pub engine: String,
}

/// Performance statistics for the engine
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineStats {
    /// Total queries executed
    pub total_queries: u64,
    /// Average execution time in milliseconds
    pub avg_execution_time_ms: f64,
    /// Peak memory usage in bytes
    pub peak_memory_bytes: u64,
    /// Number of registered tables
    pub registered_tables: usize,
}

/// Configuration for the BlazeQueryEngine
#[derive(Debug, Clone)]
pub struct EngineConfig {
    /// Target batch size for optimal performance (default: 8192)
    pub batch_size: usize,
    /// Memory limit in bytes (default: 2GB)
    pub memory_limit_bytes: usize,
    /// Number of CPU cores to use (default: num_cpus)
    pub cpu_cores: usize,
    /// Enable query plan optimization
    pub enable_optimization: bool,
}

impl Default for EngineConfig {
    fn default() -> Self {
        Self {
            batch_size: 8192,
            memory_limit_bytes: 2 * 1024 * 1024 * 1024, // 2GB
            cpu_cores: num_cpus::get(),
            enable_optimization: true,
        }
    }
}

/// High-performance query engine using DataFusion and Apache Arrow
pub struct BlazeQueryEngine {
    /// DataFusion session context for SQL execution
    ctx: Arc<RwLock<SessionContext>>,
    /// Engine configuration
    config: EngineConfig,
    /// Performance statistics
    stats: Arc<RwLock<EngineStats>>,
    /// Memory pool for tracking usage
    memory_pool: Arc<GreedyMemoryPool>,
}

impl BlazeQueryEngine {
    /// Create a new BlazeQueryEngine with default configuration
    pub async fn new() -> BlazeResult<Self> {
        Self::with_config(EngineConfig::default()).await
    }

    /// Create a new BlazeQueryEngine with custom configuration
    pub async fn with_config(config: EngineConfig) -> BlazeResult<Self> {
        info!("Initializing BlazeQueryEngine with {} CPU cores, {}MB memory limit", 
              config.cpu_cores, config.memory_limit_bytes / 1024 / 1024);

        // Create memory pool with limit
        let memory_pool = Arc::new(GreedyMemoryPool::new(config.memory_limit_bytes));

        // Configure runtime for optimal performance
        let runtime_env = RuntimeEnvBuilder::new()
            .with_memory_pool(memory_pool.clone())
            .build()?;

        // Configure session for optimal performance
        let session_config = SessionConfig::new()
            .with_target_partitions(config.cpu_cores)
            .with_batch_size(config.batch_size);

        // Create session context
        let ctx = SessionContext::new_with_config_rt(session_config, Arc::new(runtime_env));

        let stats = EngineStats {
            total_queries: 0,
            avg_execution_time_ms: 0.0,
            peak_memory_bytes: 0,
            registered_tables: 0,
        };

        Ok(Self {
            ctx: Arc::new(RwLock::new(ctx)),
            config,
            stats: Arc::new(RwLock::new(stats)),
            memory_pool,
        })
    }

    /// Execute a SQL query and return results with performance metrics
    #[instrument(skip(self, sql), fields(sql_hash = %self.hash_sql(sql)))]
    pub async fn execute_query(&self, sql: &str) -> BlazeResult<QueryResult> {
        let start_time = Instant::now();
        let start_memory = self.memory_pool.reserved();

        debug!("Executing query: {}", sql);

        let ctx = self.ctx.read().await;
        
        // Parse and plan the query
        let logical_plan = ctx.sql(sql).await?;
        
        // Get query plan for debugging (optional)
        let query_plan = if log::log_enabled!(log::Level::Debug) {
            Some(format!("{}", logical_plan.logical_plan().display_indent_schema()))
        } else {
            None
        };

        // Execute the query
        let df = logical_plan;
        let record_batches = df.collect().await?;

        // Convert results to JSON-serializable format
        let mut data = Vec::new();
        let mut total_rows = 0;

        for batch in &record_batches {
            total_rows += batch.num_rows();
            let batch_data = self.record_batch_to_json(batch)?;
            data.extend(batch_data);
        }

        let execution_time = start_time.elapsed();
        let memory_used = self.memory_pool.reserved().saturating_sub(start_memory);

        // Update statistics
        self.update_stats(execution_time.as_millis() as u64, memory_used as u64).await;

        let result = QueryResult {
            rows: total_rows,
            execution_time_ms: execution_time.as_millis() as u64,
            memory_used_bytes: memory_used as u64,
            data,
            query_plan,
            engine: "blaze".to_string(),
        };

        info!("Query completed in {}ms, {} rows, {}MB memory", 
              result.execution_time_ms, 
              result.rows,
              result.memory_used_bytes / 1024 / 1024);

        Ok(result)
    }

    /// Register a table from Arrow RecordBatches
    pub async fn register_table(&self, name: &str, batches: Vec<RecordBatch>) -> BlazeResult<()> {
        if batches.is_empty() {
            return Err(BlazeError::InvalidInput("Cannot register empty table".to_string()));
        }

        let schema = batches[0].schema();
        let total_rows: usize = batches.iter().map(|b| b.num_rows()).sum();
        let table = MemTable::try_new(schema, vec![batches])?;
        
        let ctx = self.ctx.write().await;
        ctx.register_table(name, Arc::new(table))?;

        // Update stats
        let mut stats = self.stats.write().await;
        stats.registered_tables += 1;

        info!("Registered table '{}' with {} rows", name, total_rows);

        Ok(())
    }

    /// Get current engine statistics
    pub async fn get_stats(&self) -> EngineStats {
        self.stats.read().await.clone()
    }

    /// Get available tables
    pub async fn list_tables(&self) -> BlazeResult<Vec<String>> {
        let ctx = self.ctx.read().await;
        let catalog = ctx.catalog("datafusion").ok_or_else(|| {
            BlazeError::QueryExecution(datafusion::error::DataFusionError::Plan("Catalog not found".to_string()))
        })?;
        let schema = catalog.schema("public").ok_or_else(|| {
            BlazeError::QueryExecution(datafusion::error::DataFusionError::Plan("Schema not found".to_string()))
        })?;
        let tables = schema.table_names();
        Ok(tables)
    }

    /// Validate SQL query syntax without execution
    pub async fn validate_query(&self, sql: &str) -> BlazeResult<bool> {
        let ctx = self.ctx.read().await;
        match ctx.sql(sql).await {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    /// Convert RecordBatch to JSON-serializable format (simplified)
    fn record_batch_to_json(&self, batch: &RecordBatch) -> BlazeResult<Vec<HashMap<String, serde_json::Value>>> {
        let mut result = Vec::with_capacity(batch.num_rows());
        
        // Simple conversion - can be optimized later
        for row_idx in 0..batch.num_rows() {
            let mut row = HashMap::new();
            
            for (col_idx, field) in batch.schema().fields().iter().enumerate() {
                let column = batch.column(col_idx);
                let value = match field.data_type() {
                    datafusion::arrow::datatypes::DataType::Int64 => {
                        let array = column.as_any().downcast_ref::<datafusion::arrow::array::Int64Array>().unwrap();
                        if array.is_null(row_idx) {
                            serde_json::Value::Null
                        } else {
                            serde_json::Value::Number(array.value(row_idx).into())
                        }
                    },
                    datafusion::arrow::datatypes::DataType::Float64 => {
                        let array = column.as_any().downcast_ref::<datafusion::arrow::array::Float64Array>().unwrap();
                        if array.is_null(row_idx) {
                            serde_json::Value::Null
                        } else {
                            serde_json::json!(array.value(row_idx))
                        }
                    },
                    datafusion::arrow::datatypes::DataType::Utf8 => {
                        let array = column.as_any().downcast_ref::<datafusion::arrow::array::StringArray>().unwrap();
                        if array.is_null(row_idx) {
                            serde_json::Value::Null
                        } else {
                            serde_json::Value::String(array.value(row_idx).to_string())
                        }
                    },
                    _ => serde_json::Value::String(format!("Unsupported type: {:?}", field.data_type())),
                };
                
                row.insert(field.name().clone(), value);
            }
            
            result.push(row);
        }

        Ok(result)
    }

    /// Update engine statistics
    async fn update_stats(&self, execution_time_ms: u64, memory_used: u64) {
        let mut stats = self.stats.write().await;
        
        stats.total_queries += 1;
        
        // Update average execution time
        let total_time = stats.avg_execution_time_ms * (stats.total_queries - 1) as f64 
                        + execution_time_ms as f64;
        stats.avg_execution_time_ms = total_time / stats.total_queries as f64;
        
        // Update peak memory usage
        if memory_used > stats.peak_memory_bytes {
            stats.peak_memory_bytes = memory_used;
        }
    }

    /// Generate hash for SQL query (for logging/caching)
    fn hash_sql(&self, sql: &str) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        sql.hash(&mut hasher);
        format!("{:x}", hasher.finish())
    }
}
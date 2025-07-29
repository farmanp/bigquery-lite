//! BigQuery-Lite Rust Engine
//! 
//! High-performance query engine using DataFusion for 10x performance improvement
//! over the Python implementation.

use std::sync::Arc;
use std::collections::HashMap;

use datafusion::prelude::*;
use datafusion::execution::context::SessionConfig;
use datafusion::execution::runtime_env::RuntimeEnv;
use datafusion::arrow::record_batch::RecordBatch;
use datafusion::arrow::datatypes::{Schema, Field, DataType};

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use thiserror::Error;

mod engine;
mod python_bindings;
mod error;
mod utils;

pub use engine::BlazeQueryEngine;
pub use error::{BlazeError, BlazeResult};
pub use python_bindings::*;

/// Initialize the Python module
#[pymodule]
fn bigquery_lite_engine(_py: Python, m: &PyModule) -> PyResult<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter("bigquery_lite_engine=info")
        .try_init()
        .ok(); // Ignore error if already initialized

    // Register classes and functions
    m.add_class::<PyBlazeQueryEngine>()?;
    m.add_function(wrap_pyfunction!(create_engine, m)?)?;
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_basic_functionality() {
        let engine = BlazeQueryEngine::new().await.unwrap();
        
        // This is a basic test to ensure the engine can be created
        let stats = engine.get_stats().await;
        assert_eq!(stats.total_queries, 0);
    }
}
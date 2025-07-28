//! Python FFI bindings for BlazeQueryEngine

use std::collections::HashMap;
use std::sync::Arc;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::engine::{BlazeQueryEngine, QueryResult, EngineStats, EngineConfig};
use crate::error::{BlazeError, BlazeResult, IntoPyResult};

/// Python wrapper for BlazeQueryEngine
#[pyclass(name = "BlazeQueryEngine")]
pub struct PyBlazeQueryEngine {
    engine: Arc<BlazeQueryEngine>,
}

/// Python wrapper for QueryResult
#[pyclass(name = "QueryResult")]
#[derive(Clone)]
pub struct PyQueryResult {
    #[pyo3(get)]
    pub rows: usize,
    #[pyo3(get)]
    pub execution_time_ms: u64,
    #[pyo3(get)]
    pub memory_used_bytes: u64,
    #[pyo3(get)]
    pub engine: String,
    // Store data as JSON string for simplicity
    pub data_json: String,
    query_plan: Option<String>,
}

/// Python wrapper for EngineStats
#[pyclass(name = "EngineStats")]
#[derive(Clone)]
pub struct PyEngineStats {
    #[pyo3(get)]
    pub total_queries: u64,
    #[pyo3(get)]
    pub avg_execution_time_ms: f64,
    #[pyo3(get)]
    pub peak_memory_bytes: u64,
    #[pyo3(get)]
    pub registered_tables: usize,
}

#[pymethods]
impl PyBlazeQueryEngine {
    /// Create a new BlazeQueryEngine instance
    #[new]
    fn new() -> PyResult<Self> {
        // Use sync runtime for simplicity in constructor
        let rt = tokio::runtime::Runtime::new()?;
        let engine = rt.block_on(async {
            BlazeQueryEngine::new().await.map_err(|e| PyErr::from(e))
        })?;
        
        Ok(PyBlazeQueryEngine {
            engine: Arc::new(engine),
        })
    }

    /// Execute a SQL query synchronously (simplified version)
    fn execute_query_sync(&self, sql: String) -> PyResult<PyQueryResult> {
        let rt = tokio::runtime::Runtime::new()?;
        let engine = self.engine.clone();
        
        let result = rt.block_on(async move {
            engine.execute_query(&sql).await.map_err(|e| PyErr::from(e))
        })?;
        
        // Convert to JSON string for simplicity
        let data_json = serde_json::to_string(&result.data).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON serialization error: {}", e))
        })?;
        
        Ok(PyQueryResult {
            rows: result.rows,
            execution_time_ms: result.execution_time_ms,
            memory_used_bytes: result.memory_used_bytes,
            engine: result.engine,
            data_json,
            query_plan: result.query_plan,
        })
    }

    /// Get engine statistics synchronously
    fn get_stats_sync(&self) -> PyResult<PyEngineStats> {
        let rt = tokio::runtime::Runtime::new()?;
        let engine = self.engine.clone();
        
        let stats = rt.block_on(async move {
            engine.get_stats().await
        });
        
        Ok(PyEngineStats {
            total_queries: stats.total_queries,
            avg_execution_time_ms: stats.avg_execution_time_ms,
            peak_memory_bytes: stats.peak_memory_bytes,
            registered_tables: stats.registered_tables,
        })
    }

    /// List available tables synchronously
    fn list_tables_sync(&self) -> PyResult<Vec<String>> {
        let rt = tokio::runtime::Runtime::new()?;
        let engine = self.engine.clone();
        
        let tables = rt.block_on(async move {
            engine.list_tables().await.map_err(|e| PyErr::from(e))
        })?;
        
        Ok(tables)
    }

    /// Validate SQL query syntax synchronously
    fn validate_query_sync(&self, sql: String) -> PyResult<bool> {
        let rt = tokio::runtime::Runtime::new()?;
        let engine = self.engine.clone();
        
        let is_valid = rt.block_on(async move {
            engine.validate_query(&sql).await.map_err(|e| PyErr::from(e))
        })?;
        
        Ok(is_valid)
    }

    /// Register test data for benchmarking
    fn register_test_data(&self, table_name: String, rows: usize) -> PyResult<()> {
        let rt = tokio::runtime::Runtime::new()?;
        let engine = self.engine.clone();
        
        rt.block_on(async move {
            let batches = create_test_data(rows).await.map_err(|e| PyErr::from(e))?;
            engine.register_table(&table_name, batches).await.map_err(|e| PyErr::from(e))
        })?;
        
        Ok(())
    }
}

#[pymethods]
impl PyQueryResult {
    /// Get query result data as parsed JSON
    #[getter]
    fn data(&self, py: Python) -> PyResult<PyObject> {
        let data: Vec<HashMap<String, serde_json::Value>> = serde_json::from_str(&self.data_json).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON deserialization error: {}", e))
        })?;
        
        let py_list = PyList::empty(py);
        for row in data {
            let py_dict = PyDict::new(py);
            for (key, value) in row {
                let py_value = json_value_to_python(py, &value)?;
                py_dict.set_item(key, py_value)?;
            }
            py_list.append(py_dict)?;
        }
        
        Ok(py_list.into())
    }

    /// Get query plan if available
    #[getter]
    fn query_plan(&self) -> Option<String> {
        self.query_plan.clone()
    }

    /// String representation
    fn __repr__(&self) -> String {
        format!(
            "QueryResult(rows={}, execution_time_ms={}, memory_used_mb={:.2})", 
            self.rows, 
            self.execution_time_ms,
            self.memory_used_bytes as f64 / 1024.0 / 1024.0
        )
    }
}

#[pymethods]
impl PyEngineStats {
    /// String representation
    fn __repr__(&self) -> String {
        format!(
            "EngineStats(queries={}, avg_time={:.2}ms, peak_memory={:.2}MB, tables={})",
            self.total_queries,
            self.avg_execution_time_ms,
            self.peak_memory_bytes as f64 / 1024.0 / 1024.0,
            self.registered_tables
        )
    }
}

/// Create a new engine instance (convenience function)
#[pyfunction]
pub fn create_engine() -> PyResult<PyBlazeQueryEngine> {
    PyBlazeQueryEngine::new()
}

/// Helper function to convert serde_json::Value to Python object
fn json_value_to_python(py: Python, value: &serde_json::Value) -> PyResult<PyObject> {
    match value {
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => Ok(b.into_py(py)),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.into_py(py))
            } else if let Some(f) = n.as_f64() {
                Ok(f.into_py(py))
            } else {
                Ok(n.to_string().into_py(py))
            }
        }
        serde_json::Value::String(s) => Ok(s.into_py(py)),
        serde_json::Value::Array(arr) => {
            let py_list = PyList::empty(py);
            for item in arr {
                py_list.append(json_value_to_python(py, item)?)?;
            }
            Ok(py_list.into())
        }
        serde_json::Value::Object(obj) => {
            let py_dict = PyDict::new(py);
            for (key, val) in obj {
                py_dict.set_item(key, json_value_to_python(py, val)?)?;
            }
            Ok(py_dict.into())
        }
    }
}

/// Create test data for benchmarking
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
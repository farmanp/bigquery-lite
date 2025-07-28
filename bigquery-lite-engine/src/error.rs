//! Error handling for the BlazeQueryEngine

use thiserror::Error;
use pyo3::{PyErr, PyResult};

/// Result type alias for BlazeQueryEngine operations
pub type BlazeResult<T> = Result<T, BlazeError>;

/// Comprehensive error types for the query engine
#[derive(Error, Debug)]
pub enum BlazeError {
    /// DataFusion query execution errors
    #[error("Query execution failed: {0}")]
    QueryExecution(#[from] datafusion::error::DataFusionError),

    /// Arrow data processing errors
    #[error("Arrow processing failed: {0}")]
    Arrow(#[from] datafusion::arrow::error::ArrowError),

    /// JSON serialization/deserialization errors
    #[error("JSON processing failed: {0}")]
    Json(#[from] serde_json::Error),

    /// I/O errors
    #[error("I/O operation failed: {0}")]
    Io(#[from] std::io::Error),

    /// Invalid input parameters
    #[error("Invalid input: {0}")]
    InvalidInput(String),

    /// Memory allocation or limit exceeded
    #[error("Memory error: {0}")]
    Memory(String),

    /// Query timeout
    #[error("Query timed out after {timeout_ms}ms")]
    Timeout { timeout_ms: u64 },

    /// Table not found
    #[error("Table '{table_name}' not found")]
    TableNotFound { table_name: String },

    /// Schema mismatch errors
    #[error("Schema mismatch: {0}")]
    SchemaMismatch(String),

    /// Configuration errors
    #[error("Configuration error: {0}")]
    Config(String),

    /// Python FFI errors
    #[error("Python FFI error: {0}")]
    Python(String),
}

impl From<BlazeError> for PyErr {
    fn from(err: BlazeError) -> Self {
        use pyo3::exceptions::*;
        
        match err {
            BlazeError::QueryExecution(ref e) => {
                PyRuntimeError::new_err(format!("Query execution failed: {}", e))
            }
            BlazeError::Arrow(ref e) => {
                PyRuntimeError::new_err(format!("Arrow processing failed: {}", e))
            }
            BlazeError::Json(ref e) => {
                PyValueError::new_err(format!("JSON processing failed: {}", e))
            }
            BlazeError::Io(ref e) => {
                PyIOError::new_err(format!("I/O operation failed: {}", e))
            }
            BlazeError::InvalidInput(ref msg) => {
                PyValueError::new_err(msg.clone())
            }
            BlazeError::Memory(ref msg) => {
                PyMemoryError::new_err(msg.clone())
            }
            BlazeError::Timeout { timeout_ms } => {
                PyTimeoutError::new_err(format!("Query timed out after {}ms", timeout_ms))
            }
            BlazeError::TableNotFound { ref table_name } => {
                PyKeyError::new_err(format!("Table '{}' not found", table_name))
            }
            BlazeError::SchemaMismatch(ref msg) => {
                PyValueError::new_err(format!("Schema mismatch: {}", msg))
            }
            BlazeError::Config(ref msg) => {
                PyValueError::new_err(format!("Configuration error: {}", msg))
            }
            BlazeError::Python(ref msg) => {
                PyRuntimeError::new_err(msg.clone())
            }
        }
    }
}

/// Helper trait for converting Results to Python
pub trait IntoPyResult<T> {
    fn into_py_result(self) -> PyResult<T>;
}

impl<T> IntoPyResult<T> for BlazeResult<T> {
    fn into_py_result(self) -> PyResult<T> {
        self.map_err(|e| e.into())
    }
}

/// Macro for creating BlazeError::InvalidInput with formatted message
#[macro_export]
macro_rules! invalid_input {
    ($($arg:tt)*) => {
        BlazeError::InvalidInput(format!($($arg)*))
    };
}

/// Macro for creating BlazeError::Memory with formatted message
#[macro_export]
macro_rules! memory_error {
    ($($arg:tt)*) => {
        BlazeError::Memory(format!($($arg)*))
    };
}

/// Macro for creating BlazeError::Config with formatted message
#[macro_export]
macro_rules! config_error {
    ($($arg:tt)*) => {
        BlazeError::Config(format!($($arg)*))
    };
}
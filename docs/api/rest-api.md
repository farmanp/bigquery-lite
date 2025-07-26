# REST API Reference

The BigQuery-Lite backend provides a comprehensive REST API for query execution, schema management, and data ingestion. This API powers both the web interface and CLI tool.

## Base URL and Authentication

**Base URL:** `http://localhost:8001` (default)

**Authentication:** Currently no authentication required (planned for future versions)

**Content Type:** `application/json` for JSON requests, `multipart/form-data` for file uploads

## Interactive Documentation

FastAPI provides interactive API documentation:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Core Endpoints Overview

| Category | Endpoint | Method | Purpose |
|----------|----------|--------|---------|
| **Health** | `/health` | GET | Service health check |
| **Queries** | `/queries` | POST | Submit SQL queries |
| | `/jobs/{job_id}` | GET | Get job status |
| | `/jobs/{job_id}/result` | GET | Get query results |
| | `/jobs` | GET | List recent jobs |
| **Schemas** | `/schemas/register` | POST | Register protobuf schema |
| | `/schemas` | GET | List registered schemas |
| | `/schemas/{schema_id}` | GET | Get schema details |
| | `/schemas/{schema_id}/tables/create` | POST | Create tables from schema |
| | `/schemas/{schema_id}/ingest` | POST | Ingest protobuf data |
| **System** | `/status` | GET | System status and metrics |

## Health and Status

### Health Check

Check if the service is running and engines are available.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "engines": ["duckdb", "clickhouse"],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### System Status

Get detailed system status including resource usage.

```http
GET /status
```

**Response:**
```json
{
  "status": "running",
  "available_slots": 6,
  "max_slots": 8,
  "running_jobs": 2,
  "queued_jobs": 0,
  "engines": {
    "duckdb": {
      "status": "available",
      "version": "0.9.2",
      "memory_usage_mb": 45.2
    },
    "clickhouse": {
      "status": "available",
      "version": "23.8",
      "cluster_nodes": 3,
      "active_connections": 2
    }
  },
  "uptime_seconds": 3600,
  "total_queries_executed": 156
}
```

## Query Execution

### Submit Query

Execute SQL queries on DuckDB or ClickHouse engines.

```http
POST /queries
Content-Type: application/json

{
  "sql": "SELECT COUNT(*) FROM nyc_taxi",
  "engine": "duckdb",
  "priority": 1,
  "estimated_slots": 1,
  "max_execution_time": 300
}
```

**Parameters:**
- `sql` (string, required): SQL query to execute
- `engine` (string, optional): Engine to use (`duckdb` or `clickhouse`, default: `duckdb`)
- `priority` (integer, optional): Query priority 1-5 (default: 1)
- `estimated_slots` (integer, optional): Estimated slots needed 1-10 (default: 1)
- `max_execution_time` (integer, optional): Max execution time in seconds (default: 300)

**Response:**
```json
{
  "job_id": "job_abc123def456",
  "status": "queued",
  "message": "Query submitted successfully",
  "estimated_execution_time": 2.5,
  "queue_position": 0
}
```

### Get Job Status

Check the status of a submitted query.

```http
GET /jobs/{job_id}
```

**Response (Queued):**
```json
{
  "job_id": "job_abc123def456",
  "status": "queued",
  "queue_position": 1,
  "estimated_start_time": "2024-01-15T10:32:00Z"
}
```

**Response (Running):**
```json
{
  "job_id": "job_abc123def456",
  "status": "running",
  "progress": 0.45,
  "elapsed_time": 1.23,
  "engine": "duckdb",
  "slots_used": 1
}
```

**Response (Completed):**
```json
{
  "job_id": "job_abc123def456",
  "status": "completed",
  "execution_time": 0.023,
  "rows_processed": 50000,
  "result_rows": 1,
  "engine": "duckdb"
}
```

**Response (Failed):**
```json
{
  "job_id": "job_abc123def456",
  "status": "failed",
  "error": "Table 'nonexistent_table' does not exist",
  "error_code": "TABLE_NOT_FOUND",
  "execution_time": 0.001
}
```

### Get Query Results

Retrieve the results of a completed query.

```http
GET /jobs/{job_id}/result
```

**Response:**
```json
{
  "job_id": "job_abc123def456",
  "status": "completed",
  "result": {
    "data": [
      {"count": 50000}
    ],
    "columns": [
      {"name": "count", "type": "BIGINT"}
    ],
    "rows": 1,
    "execution_time": 0.023,
    "engine": "duckdb",
    "performance_metrics": {
      "memory_used_mb": 0.1,
      "cpu_time": 0.018,
      "io_read_mb": 0.0,
      "io_write_mb": 0.0
    },
    "query_plan": "PROJECTION [count(*)]\\n  TABLE_FUNCTION nyc_taxi"
  }
}
```

### List Recent Jobs

Get a list of recent query jobs.

```http
GET /jobs?limit=10&offset=0&status=completed
```

**Query Parameters:**
- `limit` (integer, optional): Number of jobs to return (default: 50, max: 100)
- `offset` (integer, optional): Number of jobs to skip (default: 0)
- `status` (string, optional): Filter by status (`queued`, `running`, `completed`, `failed`)
- `engine` (string, optional): Filter by engine (`duckdb`, `clickhouse`)

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "job_abc123def456",
      "status": "completed",
      "sql": "SELECT COUNT(*) FROM nyc_taxi",
      "engine": "duckdb",
      "execution_time": 0.023,
      "created_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

## Schema Management

### Register Schema

Register a protobuf schema for table creation and data ingestion.

```http
POST /schemas/register
Content-Type: multipart/form-data

form data:
- proto_file: (file) user_events.proto
- schema_file: (file, optional) user_events.schema  
- table_name: user_events
- database_name: bigquery_lite
```

**Form Parameters:**
- `proto_file` (file, required): Protobuf definition file (.proto)
- `schema_file` (file, optional): Pre-generated BigQuery schema file (.schema)
- `table_name` (string, required): Target table name
- `database_name` (string, optional): Target database name (default: "bigquery_lite")

**Response:**
```json
{
  "schema_id": "schema_a1b2c3d4e5f6",
  "table_name": "user_events",
  "database_name": "bigquery_lite",
  "version_hash": "a1b2c3d4e5f67890abcdef1234567890",
  "field_count": 8,
  "created_at": "2024-01-15T10:30:00Z",
  "proto_content": "syntax = \"proto3\";\\npackage events;...",
  "bigquery_schema": {
    "fields": [
      {
        "name": "event_id",
        "type": "INTEGER",
        "mode": "REQUIRED"
      }
    ]
  }
}
```

### List Schemas

Get all registered schemas.

```http
GET /schemas?limit=20&offset=0
```

**Query Parameters:**
- `limit` (integer, optional): Number of schemas to return (default: 50)
- `offset` (integer, optional): Number of schemas to skip (default: 0)
- `database_name` (string, optional): Filter by database name

**Response:**
```json
{
  "schemas": [
    {
      "schema_id": "schema_a1b2c3d4e5f6",
      "table_name": "user_events",
      "database_name": "bigquery_lite",
      "field_count": 8,
      "total_versions": 2,
      "latest_version": "a1b2c3d4e5f67890abcdef1234567890",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T11:45:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### Get Schema Details

Get detailed information about a specific schema.

```http
GET /schemas/{schema_id}
```

**Response:**
```json
{
  "schema_id": "schema_a1b2c3d4e5f6",
  "table_name": "user_events",
  "database_name": "bigquery_lite",
  "proto_content": "syntax = \"proto3\";\\npackage events;...",
  "bigquery_schema": {
    "fields": [
      {
        "name": "event_id",
        "type": "INTEGER",
        "mode": "REQUIRED",
        "description": "Unique event identifier"
      },
      {
        "name": "user_id", 
        "type": "STRING",
        "mode": "REQUIRED"
      },
      {
        "name": "profile",
        "type": "RECORD",
        "mode": "NULLABLE",
        "fields": [
          {
            "name": "name",
            "type": "STRING",
            "mode": "NULLABLE"
          }
        ]
      }
    ]
  },
  "versions": [
    {
      "version_hash": "a1b2c3d4e5f67890abcdef1234567890",
      "created_at": "2024-01-15T11:45:00Z",
      "field_count": 8
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z"
}
```

### Create Tables from Schema

Create database tables from a registered schema.

```http
POST /schemas/{schema_id}/tables/create
Content-Type: application/json

{
  "engines": ["duckdb", "clickhouse"],
  "if_not_exists": true,
  "create_flattened_view": false
}
```

**Parameters:**
- `engines` (array, optional): List of engines to create tables in (default: ["duckdb"])
- `if_not_exists` (boolean, optional): Use IF NOT EXISTS clause (default: true)
- `create_flattened_view` (boolean, optional): Create flattened view for nested schemas (default: false)

**Response:**
```json
{
  "schema_id": "schema_a1b2c3d4e5f6",
  "table_name": "user_events",
  "database_name": "bigquery_lite",
  "results": {
    "duckdb": {
      "success": true,
      "sql_executed": "CREATE TABLE IF NOT EXISTS user_events (...)",
      "execution_time": 0.023,
      "rows_affected": 0
    },
    "clickhouse": {
      "success": true,
      "sql_executed": "CREATE TABLE IF NOT EXISTS user_events (...) ENGINE = MergeTree() ORDER BY event_id",
      "execution_time": 0.156,
      "rows_affected": 0
    }
  },
  "flattened_view_created": false,
  "total_engines": 2,
  "successful_engines": 2,
  "created_at": "2024-01-15T10:32:00Z"
}
```

## Data Ingestion

### Ingest Protobuf Data

Ingest binary protobuf data into tables.

```http
POST /schemas/{schema_id}/ingest
Content-Type: multipart/form-data

form data:
- pb_file: (file) user_events.pb
- target_engine: duckdb
- batch_size: 1000
- create_table_if_not_exists: true
```

**Form Parameters:**
- `pb_file` (file, required): Binary protobuf data file (.pb)
- `target_engine` (string, optional): Target engine (default: "duckdb")
- `batch_size` (integer, optional): Records per batch (default: 1000)
- `create_table_if_not_exists` (boolean, optional): Create table if missing (default: true)

**Response:**
```json
{
  "job_id": "ingest_job_xyz789",
  "schema_id": "schema_a1b2c3d4e5f6",
  "status": "completed",
  "records_processed": 50000,
  "records_inserted": 49997,
  "processing_time": 2.456,
  "target_engine": "duckdb",
  "target_table": "bigquery_lite.user_events",
  "errors": [
    "Invalid timestamp format in record 1234",
    "Missing required field 'user_id' in record 5678",
    "Value out of range for field 'age' in record 9012"
  ],
  "performance_metrics": {
    "records_per_second": 20325,
    "memory_used_mb": 128.5,
    "io_write_mb": 45.2
  },
  "created_at": "2024-01-15T10:35:00Z",
  "completed_at": "2024-01-15T10:37:30Z"
}
```

## Error Responses

All endpoints return consistent error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid SQL syntax: missing FROM clause",
  "error_code": "INVALID_SQL",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 404 Not Found
```json
{
  "detail": "Job not found: job_nonexistent",
  "error_code": "JOB_NOT_FOUND",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "sql"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "error_code": "VALIDATION_ERROR"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Database connection failed",
  "error_code": "DATABASE_ERROR",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Rate Limiting and Quotas

Currently no rate limiting is implemented, but planned features include:

- **Query rate limiting**: Maximum queries per minute per client
- **Resource quotas**: Memory and CPU usage limits
- **Concurrent job limits**: Maximum simultaneous queries per client

## Data Types

### Query Result Data Types

| BigQuery Type | JSON Type | Example |
|---------------|-----------|---------|
| INTEGER | number | `123456` |
| FLOAT | number | `123.456` |
| STRING | string | `"Hello World"` |
| BOOLEAN | boolean | `true` |
| TIMESTAMP | string (ISO 8601) | `"2024-01-15T10:30:00Z"` |
| DATE | string (YYYY-MM-DD) | `"2024-01-15"` |
| ARRAY | array | `[1, 2, 3]` |
| RECORD | object | `{"name": "value"}` |

### Schema Field Types

Supported BigQuery schema field types:
- `INTEGER`, `INT64` - 64-bit integers  
- `FLOAT`, `FLOAT64` - Double precision floating point
- `STRING` - Variable length strings
- `BOOLEAN`, `BOOL` - Boolean values
- `TIMESTAMP` - Timestamp with timezone
- `DATE` - Date only
- `NUMERIC` - High precision decimal
- `RECORD` - Nested structures
- `REPEATED` - Arrays of values

## Performance Considerations

### Query Optimization
- Use `LIMIT` clauses for large result sets
- Consider using ClickHouse for analytical queries over large datasets
- Use DuckDB for development and exploratory analysis

### Batch Operations
- Use appropriate batch sizes for data ingestion (1000-10000 records)
- Consider engine capabilities when choosing batch sizes
- Monitor memory usage during large operations

### Caching
- Query plans are cached for identical queries
- Schema translations are cached after first use
- Consider using query result caching for frequently executed queries

## Next Steps

- **[Query Endpoints](queries.md)** - Detailed query execution documentation
- **[Schema Endpoints](schemas.md)** - Advanced schema management
- **[Data Ingestion](ingestion.md)** - Protobuf data ingestion details
- **[CLI Tool](../user-guide/cli-tool.md)** - Command-line interface usage
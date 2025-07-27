# FastAPI Backend Architecture

## Overview

The FastAPI backend serves as the central nervous system of BigQuery-Lite, providing a unified REST API interface that coordinates between the web frontend, CLI tools, and multiple query engines. Built with modern Python async/await patterns, it handles concurrent query execution, schema management, and real-time job status updates.

## Core Application Structure

### Application Initialization (`backend/app.py`)

```python
# Lifespan Management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup: Initialize runners, schema components, background jobs
    # Shutdown: Cleanup connections and resources
```

**Key Initialization Steps:**
1. **Database Setup**: Initialize SQLite for job history storage
2. **Schema Components**: Load SchemaRegistry, SchemaTranslator, ProtobufIngester
3. **Query Runners**: Initialize DuckDB and ClickHouse engines
4. **Background Processing**: Start async job queue processor
5. **Sample Data**: Load NYC taxi dataset for demonstrations

### Application Configuration

```python
app = FastAPI(
    title="BigQuery-Lite Backend",
    description="Backend API for BigQuery-like local analytics",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## API Endpoint Structure

### 1. Health & Status Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | API status and available engines |
| `/health` | GET | Docker health check endpoint |
| `/status` | GET | System metrics and engine availability |

### 2. Query Execution Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/queries` | POST | Submit SQL query for execution |
| `/jobs/{job_id}` | GET | Get job status and progress |
| `/jobs/{job_id}/result` | GET | Retrieve query results |
| `/jobs` | GET | List recent job history |
| `/examples` | GET | Get sample queries |

**Query Execution Flow:**
```python
@app.post("/queries", response_model=QueryResponse)
async def submit_query(query_request: QueryRequest):
    """Submit a query for execution"""
    # 1. Validate request parameters
    # 2. Generate unique job ID
    # 3. Queue job for background processing
    # 4. Return job ID immediately (async pattern)
```

### 3. Schema Management Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/schemas/register` | POST | Register new protobuf schema |
| `/schemas` | GET | List all registered schemas |
| `/schemas/{schema_id}` | GET | Get schema details and metadata |
| `/schemas/{schema_id}/tables/create` | POST | Create table from schema |
| `/schemas/{schema_id}/ingest` | POST | Ingest protobuf data |
| `/schemas/{schema_id}` | DELETE | Remove schema registration |

## Request/Response Models

### Query Models
```python
class QueryRequest(BaseModel):
    sql: str = Field(..., description="SQL query to execute")
    engine: str = Field(default="duckdb", description="Engine: duckdb or clickhouse")
    priority: int = Field(default=1, ge=1, le=5, description="Query priority")
    estimated_slots: int = Field(default=1, ge=1, le=10, description="Estimated slots")
    max_execution_time: int = Field(default=300, description="Max execution time (seconds)")

class QueryResponse(BaseModel):
    job_id: str
    status: str
    message: str
    estimated_completion_time: Optional[datetime]
```

### Schema Models
```python
class SchemaRegistrationRequest(BaseModel):
    table_name: str
    database_name: str = "bigquery_lite"
    description: Optional[str] = None

class SchemaRegistrationResponse(BaseModel):
    schema_id: str
    message: str
    table_name: str
    database_name: str
    field_count: int
```

## Background Job Processing

### Job Queue Architecture

```python
# Global job queue and processing state
job_queue = asyncio.Queue()
active_jobs = {}
job_history_db = {}

async def process_job_queue():
    """Background task to process queued jobs"""
    while True:
        try:
            job = await job_queue.get()
            await execute_job(job)
        except Exception as e:
            logger.error(f"Job processing error: {e}")
        finally:
            job_queue.task_done()
```

### Job Execution Flow

1. **Job Submission**: API endpoint receives query → validates → creates job → adds to queue
2. **Background Processing**: Dedicated async task picks up jobs → executes on appropriate engine
3. **Status Updates**: Job status stored in memory and database for real-time polling
4. **Result Storage**: Query results cached in memory with execution metadata

## Dependency Injection Pattern

The application uses FastAPI's dependency injection for clean separation of concerns:

```python
async def get_schema_registry() -> SchemaRegistry:
    """Dependency injection for schema registry"""
    return schema_registry

async def get_runners() -> Dict[str, Any]:
    """Dependency injection for database runners"""
    return runners

# Usage in endpoints
@app.post("/schemas/register")
async def register_schema(
    registry: SchemaRegistry = Depends(get_schema_registry),
    translator: SchemaTranslator = Depends(get_schema_translator)
):
    # Endpoint implementation with injected dependencies
```

## Error Handling Strategy

### Centralized Exception Handling

```python
class SchemaRegistryError(Exception):
    """Custom exception for schema registry operations"""
    pass

class ProtobufDecodingError(Exception):
    """Exception for protobuf decoding errors"""
    pass

# HTTP Exception mapping
try:
    result = await some_operation()
except SchemaRegistryError as e:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Schema operation failed: {e}"
    )
```

### Error Response Format

All endpoints return consistent error responses:
```json
{
  "detail": "Human-readable error message",
  "error_code": "SCHEMA_VALIDATION_FAILED",
  "timestamp": "2024-01-26T10:30:00Z"
}
```

## Database Storage

### Job History Database (SQLite)

```sql
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    sql TEXT NOT NULL,
    engine TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    execution_time_ms INTEGER,
    rows_returned INTEGER
);
```

### Schema Registry Database

- **Schemas Table**: Stores schema metadata and versions
- **Schema Versions Table**: Tracks schema evolution over time
- **Engine Tables Table**: Records which engines have tables created

## Performance Considerations

### Async/Await Pattern
- **Non-blocking Operations**: All I/O operations use async patterns
- **Concurrent Execution**: Multiple queries can execute simultaneously
- **Background Processing**: Long-running operations don't block API responses

### Connection Pooling
- **Database Connections**: Reuse connections across requests
- **ClickHouse Client**: Persistent connection with configurable timeouts
- **DuckDB Sessions**: Thread-safe connection management

### Memory Management
- **Result Caching**: Query results cached in memory with configurable TTL
- **Job Cleanup**: Completed jobs removed from active memory after timeout
- **Resource Limits**: Configurable memory limits for query execution

## Configuration & Environment

### Environment Variables
```bash
# ClickHouse Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=password

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
MAX_CONCURRENT_JOBS=10
```

### Development vs Production
- **Development**: Auto-reload enabled, debug logging, sample data loading
- **Production**: Optimized settings, structured logging, health checks

## Security Considerations

### Current Implementation
- **CORS**: Configured for local development (localhost:3000)
- **Input Validation**: Pydantic models validate all inputs
- **SQL Injection**: Parameterized queries and engine-level protection

### Planned Security Features
- **Authentication**: JWT-based user authentication
- **Authorization**: Role-based access control for schemas and queries
- **Rate Limiting**: Request throttling per user/IP
- **Audit Logging**: Comprehensive operation logging

## Monitoring & Observability

### Health Checks
```python
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "engines": {
            "duckdb": runners['duckdb'].is_initialized,
            "clickhouse": runners['clickhouse'].is_initialized
        }
    }
```

### Metrics Collection
- **Query Execution Times**: Tracked per engine and query type
- **Error Rates**: HTTP status codes and exception tracking
- **Resource Usage**: Memory and CPU utilization monitoring
- **Job Queue Metrics**: Queue depth and processing times

## API Documentation

### Auto-Generated Documentation
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI Spec**: Auto-generated from Pydantic models

### Interactive Testing
The Swagger UI provides a complete interactive interface for testing all endpoints with real request/response examples and schema validation.

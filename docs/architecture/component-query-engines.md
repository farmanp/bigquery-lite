# Query Engine Architecture

## Overview

BigQuery-Lite implements a **plugin-based query engine architecture** that provides a unified interface to multiple database backends. This design allows users to choose the most appropriate engine for their workload while maintaining consistent API interactions and query patterns.

## Engine Abstraction Pattern

### Common Interface Design

All query engines implement a consistent interface pattern:

```python
class QueryEngine:
    async def initialize(self) -> None:
        """Initialize engine connection and setup"""
        
    async def execute_query(self, sql: str) -> Dict[str, Any]:
        """Execute SQL query and return results with metadata"""
        
    async def cleanup(self) -> None:
        """Clean up connections and resources"""
        
    def is_healthy(self) -> bool:
        """Check engine health status"""
```

### Engine Registration

Engines are registered in the FastAPI application during startup:

```python
# Global runners dictionary
runners = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database runners
    runners['duckdb'] = DuckDBRunner()
    runners['clickhouse'] = ClickHouseRunner()
    
    # Initialize each engine
    await runners['duckdb'].initialize()
    await runners['clickhouse'].initialize()
```

## DuckDB Engine Implementation

### Purpose and Use Cases

**DuckDB** serves as the **embedded analytics engine** optimized for:
- Interactive query development and testing
- Single-machine analytics workloads
- Fast aggregations on small to medium datasets (< 100GB)
- Development environments without external dependencies

### Architecture (`backend/runners/duckdb_runner.py`)

```python
class DuckDBRunner:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path          # In-memory or file-based storage
        self.connection = None           # DuckDB connection object
        self.is_initialized = False      # Initialization state
```

### Key Features

**Memory-Optimized Execution**
```python
# Configure memory limits and optimization
self.connection.execute("PRAGMA memory_limit='2GB'")
self.connection.execute("PRAGMA enable_profiling")
self.connection.execute("PRAGMA profiling_mode = 'detailed'")
```

**Sample Data Loading**
```python
# Automatically load NYC taxi dataset for demonstrations
if os.path.exists("../data/nyc_taxi.parquet"):
    self.connection.execute(f"""
        CREATE VIEW IF NOT EXISTS nyc_taxi AS 
        SELECT * FROM read_parquet('{data_path}')
    """)
```

**Query Execution with Profiling**
```python
async def execute_query(self, sql: str) -> Dict[str, Any]:
    start_time = time.time()
    
    # Execute query and capture results
    result = self.connection.execute(sql).fetchall()
    columns = [desc[0] for desc in self.connection.description]
    
    # Get query plan and performance metrics
    query_plan = self.connection.execute("PRAGMA last_profiling_output").fetchall()
    
    return {
        "columns": columns,
        "data": result,
        "execution_time_ms": (time.time() - start_time) * 1000,
        "query_plan": query_plan,
        "row_count": len(result),
        "engine": "duckdb"
    }
```

### DuckDB Capabilities

- **Columnar Storage**: Efficient analytical operations
- **Vector Processing**: SIMD optimizations for aggregations
- **Parquet Integration**: Native support for columnar file formats
- **SQL Compatibility**: PostgreSQL-compatible SQL dialect
- **Embedded Deployment**: No external server dependencies

## ClickHouse Engine Implementation

### Purpose and Use Cases

**ClickHouse** serves as the **distributed OLAP engine** optimized for:
- Large-scale analytical workloads (> 100GB datasets)
- Time-series and log analytics
- Real-time data ingestion and querying
- Production analytics environments

### Architecture (`backend/runners/clickhouse_runner.py`)

```python
class ClickHouseRunner:
    def __init__(self, host: str = None, port: int = None):
        # Environment-based configuration
        self.host = host or os.getenv('CLICKHOUSE_HOST', 'localhost')
        self.port = port or int(os.getenv('CLICKHOUSE_PORT', '8123'))
        self.username = os.getenv('CLICKHOUSE_USER', 'admin')
        self.password = os.getenv('CLICKHOUSE_PASSWORD', 'password')
        self.client = None
```

### Connection Management

```python
async def initialize(self):
    # Create ClickHouse client with timeout configuration
    self.client = clickhouse_connect.get_client(
        host=self.host,
        port=self.port,
        username=self.username,
        password=self.password,
        connect_timeout=10,
        send_receive_timeout=30
    )
    
    # Test connection and setup database
    result = self.client.command("SELECT 1")
    self.client.command("CREATE DATABASE IF NOT EXISTS bigquery_lite")
```

### Sample Data Setup

```python
# Create ClickHouse-optimized table structure
self.client.command("""
    CREATE TABLE IF NOT EXISTS nyc_taxi (
        id UInt64,
        payment_type String,
        fare_amount Float64,
        trip_distance Float64,
        total_amount Float64,
        passenger_count UInt8,
        tpep_pickup_datetime DateTime,
        tpep_dropoff_datetime DateTime,
        tip_amount Float64
    ) ENGINE = MergeTree()
    ORDER BY (tpep_pickup_datetime, id)
""")
```

### Query Execution with Metrics

```python
async def execute_query(self, sql: str) -> Dict[str, Any]:
    start_time = time.time()
    
    # Execute query with format specification
    result = self.client.query(sql, settings={'output_format_json_quote_64bit_integers': 0})
    
    # Collect execution statistics
    execution_stats = {
        "rows_read": result.summary.get('read_rows', 0),
        "bytes_read": result.summary.get('read_bytes', 0),
        "execution_time_ms": (time.time() - start_time) * 1000,
        "memory_usage": result.summary.get('memory_usage', 0)
    }
    
    return {
        "columns": result.column_names,
        "data": result.result_rows,
        "execution_stats": execution_stats,
        "row_count": len(result.result_rows),
        "engine": "clickhouse"
    }
```

### ClickHouse Capabilities

- **Columnar Storage**: Optimized for analytical queries
- **Distributed Processing**: Horizontal scaling across multiple nodes
- **Real-time Ingestion**: High-throughput data ingestion
- **Compression**: Advanced compression algorithms
- **SQL Extensions**: Specialized functions for analytics

## Query Routing Logic

### Engine Selection Strategy

The query router selects the appropriate engine based on:

```python
async def route_query(sql: str, preferred_engine: str) -> str:
    """Route query to appropriate engine"""
    
    # Respect user's explicit engine choice
    if preferred_engine in runners and runners[preferred_engine].is_healthy():
        return preferred_engine
    
    # Fallback logic
    if runners['duckdb'].is_healthy():
        return 'duckdb'
    elif runners['clickhouse'].is_healthy():
        return 'clickhouse'
    else:
        raise HTTPException(status_code=503, detail="No healthy engines available")
```

### Engine-Specific Optimizations

**DuckDB Optimizations:**
- Memory-efficient execution for small datasets
- Automatic query plan optimization
- Vectorized operations for aggregations

**ClickHouse Optimizations:**
- Distributed query execution
- Advanced compression for storage efficiency
- Specialized time-series functions

## Error Handling and Fallback

### Engine Health Monitoring

```python
class EngineHealthChecker:
    async def check_engine_health(self, engine_name: str) -> bool:
        try:
            engine = runners[engine_name]
            test_result = await engine.execute_query("SELECT 1")
            return test_result is not None
        except Exception as e:
            logger.warning(f"Engine {engine_name} health check failed: {e}")
            return False
```

### Graceful Degradation

```python
async def execute_with_fallback(sql: str, preferred_engine: str):
    """Execute query with automatic fallback"""
    
    engines_to_try = [preferred_engine]
    if preferred_engine != 'duckdb':
        engines_to_try.append('duckdb')  # DuckDB as fallback
    
    for engine_name in engines_to_try:
        try:
            if runners[engine_name].is_healthy():
                return await runners[engine_name].execute_query(sql)
        except Exception as e:
            logger.warning(f"Query failed on {engine_name}: {e}")
            continue
    
    raise HTTPException(status_code=503, detail="All engines failed")
```

## Performance Characteristics

### DuckDB Performance Profile

| Operation Type | Performance | Use Case |
|----------------|-------------|----------|
| Small Aggregations (< 1GB) | Excellent | Interactive analytics |
| Complex JOINs | Very Good | Data exploration |
| Window Functions | Excellent | Time-series analysis |
| Concurrent Queries | Good | Development environments |

### ClickHouse Performance Profile

| Operation Type | Performance | Use Case |
|----------------|-------------|----------|
| Large Aggregations (> 10GB) | Excellent | Production analytics |
| Time-series Queries | Outstanding | Log analytics |
| Real-time Ingestion | Excellent | Streaming data |
| Distributed JOINs | Very Good | Large-scale analytics |

## Extension Points

### Adding New Engines

The architecture supports adding new query engines:

1. **Implement Common Interface**
   ```python
   class PostgreSQLRunner:
       async def initialize(self): ...
       async def execute_query(self, sql: str): ...
       async def cleanup(self): ...
   ```

2. **Register in Application**
   ```python
   runners['postgresql'] = PostgreSQLRunner()
   ```

3. **Update Frontend Options**
   ```javascript
   const engines = ['duckdb', 'clickhouse', 'postgresql'];
   ```

### Custom Query Optimizations

Engine-specific query optimizations can be added:

```python
class QueryOptimizer:
    def optimize_for_engine(self, sql: str, engine: str) -> str:
        if engine == 'clickhouse':
            # Add ClickHouse-specific optimizations
            return self.add_clickhouse_hints(sql)
        elif engine == 'duckdb':
            # Add DuckDB-specific optimizations
            return self.add_duckdb_pragmas(sql)
        return sql
```

## Future Enhancements

### Planned Engine Features

- **Query Caching**: Cross-engine result caching
- **Cost-Based Routing**: Automatic engine selection based on query complexity
- **Federation**: Cross-engine JOINs and data movement
- **Custom Functions**: User-defined functions across engines
- **Monitoring**: Engine-specific performance metrics and alerting

# BigQuery-Lite System Design

## Overview

BigQuery-Lite is a local analytics platform that replicates Google BigQuery's core functionality using open-source technologies. The system provides a familiar BigQuery-like experience while running entirely on local infrastructure.

## Design Principles

### 1. **Simplicity First**
- Zero-configuration startup with Docker Compose
- Intuitive BigQuery-inspired user interface
- Minimal learning curve for BigQuery users

### 2. **Performance & Scalability**
- Dual engine architecture for different use cases
- Efficient columnar storage and query processing
- Horizontal scaling capabilities with ClickHouse

### 3. **Developer Experience**
- Modern web interface with professional SQL editor
- Real-time query execution and results
- Comprehensive API for programmatic access

### 4. **Educational Value**
- Demonstrates distributed analytics concepts
- Provides hands-on experience with OLAP systems
- Showcases modern data engineering patterns

## System Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │    │     Backend     │    │   Data Layer    │
│   (React UI)    │◄──►│   (FastAPI)     │◄──►│  DuckDB/ClickH  │
│   Port 3000     │    │   Port 8001     │    │   Port 8123     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Monaco Editor  │    │ Job Scheduler   │    │ Schema Registry │
│  SQL Syntax     │    │ Query Queue     │    │ Metadata Store  │
│  Real-time UI   │    │ Slot Management │    │ Data Catalog    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Details

#### Frontend Layer
- **Technology**: React 18 with modern hooks
- **Editor**: Monaco Editor (VS Code engine) with SQL syntax highlighting
- **State Management**: React Context API for global state
- **Real-time Updates**: WebSocket connections for live query status
- **Responsive Design**: Mobile-friendly interface

#### Backend Layer
- **Framework**: FastAPI with async/await support
- **API Design**: RESTful endpoints with OpenAPI documentation
- **Job Management**: Queue-based system with slot allocation
- **Authentication**: JWT-based authentication (optional)
- **Monitoring**: Built-in health checks and metrics

#### Data Layer
- **DuckDB**: Embedded analytical database for fast local queries
- **ClickHouse**: Distributed columnar database for scalable analytics
- **Storage**: Parquet files for efficient columnar data storage
- **Schema Registry**: SQLite-based metadata and schema management

## Core Components

### 1. Query Execution Engine

#### Query Flow
```
User SQL Query
      ↓
   Validation & Parsing
      ↓
   Engine Selection (DuckDB/ClickHouse)
      ↓
   Job Creation & Queuing
      ↓
   Slot Allocation
      ↓
   Query Execution
      ↓
   Result Processing
      ↓
   Response to Frontend
```

#### Engine Selection Logic
- **DuckDB**: Default for development, small datasets, single-user scenarios
- **ClickHouse**: Production deployments, large datasets, multi-user access
- **User Choice**: Manual engine selection via UI

### 2. Slot-Based Scheduling

Simulates BigQuery's slot-based resource management:

```python
class SlotManager:
    def __init__(self, max_slots: int = 8):
        self.max_slots = max_slots
        self.active_jobs = {}
        self.queue = asyncio.Queue()
    
    async def acquire_slot(self, job_id: str) -> bool:
        if len(self.active_jobs) < self.max_slots:
            self.active_jobs[job_id] = time.time()
            return True
        await self.queue.put(job_id)
        return False
```

### 3. Schema Registry

Centralized metadata management:

```sql
-- Schema storage structure
CREATE TABLE schemas (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    definition JSON NOT NULL,
    engine TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tables (
    id INTEGER PRIMARY KEY,
    schema_id INTEGER REFERENCES schemas(id),
    name TEXT NOT NULL,
    columns JSON NOT NULL,
    row_count INTEGER,
    size_bytes INTEGER
);
```

### 4. Data Ingestion Pipeline

#### Supported Formats
- **Parquet**: Primary format for analytical workloads
- **CSV**: Common data exchange format
- **JSON**: Semi-structured data support
- **Protocol Buffers**: Schema-aware binary format

#### Ingestion Flow
```
Data Source → Format Detection → Schema Inference → Validation → Storage → Catalog Update
```

## Database Engine Details

### DuckDB Integration

#### Advantages
- **Zero Configuration**: No setup required, embedded in Python
- **High Performance**: Optimized for analytical queries
- **Rich SQL Support**: Window functions, CTEs, JSON processing
- **Memory Efficient**: Intelligent caching and memory management

#### Configuration
```python
import duckdb

# Connection with optimizations
conn = duckdb.connect(database=':memory:', read_only=False)
conn.execute("PRAGMA threads=4")
conn.execute("PRAGMA memory_limit='2GB'")
conn.execute("PRAGMA enable_optimizer=true")
```

#### Use Cases
- Development and testing environments
- Data exploration and prototyping
- Single-user analytics scenarios
- Datasets up to ~1GB

### ClickHouse Integration

#### Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Coordinator    │    │    Worker 1     │    │    Worker 2     │
│   (Primary)     │◄──►│   (Replica)     │◄──►│   (Replica)     │
│   Port 8123     │    │   Port 8124     │    │   Port 8125     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### Table Engines
- **MergeTree**: Primary engine for analytical tables
- **ReplicatedMergeTree**: Distributed tables with replication
- **SummingMergeTree**: Pre-aggregated summary tables
- **MaterializedView**: Real-time aggregations

#### Optimization Strategies
```sql
-- Optimized table creation
CREATE TABLE analytics_data (
    timestamp DateTime,
    user_id UInt64,
    event_type String,
    properties Map(String, String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, user_id, event_type)
SETTINGS index_granularity = 8192;
```

## API Design

### RESTful Endpoints

#### Core Query API
```http
POST /api/v1/queries
Content-Type: application/json

{
  "sql": "SELECT COUNT(*) FROM users",
  "engine": "duckdb",
  "max_runtime_seconds": 300
}

Response:
{
  "job_id": "job_123",
  "status": "queued",
  "created_at": "2024-01-26T10:00:00Z"
}
```

#### Job Management
```http
GET /api/v1/jobs/{job_id}
GET /api/v1/jobs/{job_id}/result
GET /api/v1/jobs/{job_id}/plan
DELETE /api/v1/jobs/{job_id}
```

#### Schema Management
```http
GET /api/v1/schemas
POST /api/v1/schemas
GET /api/v1/schemas/{schema_name}/tables
POST /api/v1/tables/{table_name}/data
```

### WebSocket API

Real-time query status updates:

```javascript
const ws = new WebSocket('ws://localhost:8001/ws/jobs/{job_id}');
ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    // Handle status updates: queued, running, completed, failed
};
```

## Data Flow Architecture

### Query Processing Pipeline

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   SQL       │──▶│ Validation  │──▶│  Planning   │──▶│ Execution   │
│   Parsing   │   │  & Auth     │   │ & Optimize  │   │ & Results   │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

### Data Ingestion Pipeline

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Source    │──▶│   Format    │──▶│   Schema    │──▶│   Storage   │
│   Data      │   │ Detection   │   │ Inference   │   │ & Catalog   │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

## Security Considerations

### Authentication & Authorization
- JWT-based authentication for API access
- Role-based access control (RBAC) for schema/table permissions
- API key management for programmatic access

### Data Protection
- Input validation and SQL injection prevention
- Query timeout and resource limits
- Data access logging and audit trails

### Network Security
- HTTPS/TLS encryption for web traffic
- Secure WebSocket connections (WSS)
- Docker network isolation

## Performance Optimization

### Query Optimization
- **Columnar Storage**: Efficient scanning and compression
- **Predicate Pushdown**: Filter operations at storage layer
- **Vectorized Execution**: SIMD operations for fast processing
- **Query Caching**: Result caching for repeated queries

### System Optimization
- **Connection Pooling**: Efficient database connection management
- **Async Processing**: Non-blocking I/O operations
- **Resource Management**: Memory and CPU usage monitoring
- **Load Balancing**: Distribute queries across ClickHouse workers

### Monitoring & Observability
- Query execution metrics and profiling
- System resource monitoring (CPU, memory, disk)
- Real-time performance dashboards
- Query plan analysis and optimization suggestions

## Deployment Architecture

### Development Environment
```yaml
# docker-compose.yml structure
services:
  frontend:     # React development server
  backend:      # FastAPI with hot reload
  duckdb:       # Embedded (no separate container)
  jupyter:      # Optional notebooks
```

### Production Environment
```yaml
services:
  frontend:             # Nginx serving built React app
  backend:              # Gunicorn + FastAPI
  clickhouse-server:    # Primary ClickHouse coordinator
  clickhouse-worker1:   # ClickHouse replica node
  clickhouse-worker2:   # ClickHouse replica node
  load-balancer:        # Nginx load balancer
  monitoring:           # Prometheus + Grafana
```

## Scalability Considerations

### Horizontal Scaling
- **ClickHouse Sharding**: Distribute data across multiple nodes
- **Backend Scaling**: Multiple FastAPI instances behind load balancer
- **Stateless Design**: No server-side session state

### Vertical Scaling
- **Memory Optimization**: Efficient memory usage in DuckDB
- **CPU Utilization**: Multi-threaded query processing
- **Storage Optimization**: Compressed columnar formats

### Resource Management
- **Queue Management**: Prevent system overload with job queues
- **Slot Allocation**: Simulate BigQuery's resource allocation
- **Auto-scaling**: Docker Swarm or Kubernetes for dynamic scaling

## Extension Points

### Custom Functions
```python
# DuckDB UDF registration
def custom_function(param1, param2):
    return param1 * param2

conn.create_function('custom_func', custom_function)
```

### Plugin Architecture
- **Data Connectors**: Custom data source integrations
- **Authentication Providers**: SSO and identity provider integration
- **Export Formats**: Additional result export capabilities
- **Visualization**: Custom chart and dashboard components

## Future Enhancements

### Planned Features
- **Machine Learning**: SQL-based ML model training and inference
- **Stream Processing**: Real-time data processing capabilities
- **Data Lineage**: Track data transformation and dependencies
- **Advanced Security**: Column-level access controls

### Technical Improvements
- **Query Optimization**: Advanced query planner and optimizer
- **Caching Layer**: Distributed result caching with Redis
- **Backup & Recovery**: Automated data backup and restoration
- **High Availability**: Multi-region deployment support

---

This design document serves as the technical foundation for BigQuery-Lite development and provides guidance for contributors and users understanding the system architecture.
# BigQuery-Lite System Overview

## Purpose and Vision

BigQuery-Lite is a **local analytics engine** that brings BigQuery-style functionality to development and testing environments. It provides a familiar BigQuery-like interface while running entirely on local infrastructure, eliminating the need for cloud dependencies during development.

### Key Value Propositions

1. **Local Development**: Run BigQuery-style analytics without cloud connectivity
2. **Multi-Engine Support**: Choose between DuckDB (embedded) and ClickHouse (distributed) engines
3. **Schema Management**: Protobuf-first schema definition with automatic table generation
4. **Web Interface**: Professional SQL editor with real-time execution and results visualization
5. **API-First**: RESTful backend enables programmatic access and CLI tools

## Architectural Goals

### 🎯 Core Design Principles

- **Modularity**: Clean separation between UI, API, execution engines, and storage layers
- **Engine Agnostic**: Unified interface supports multiple query engines (DuckDB, ClickHouse)
- **Schema-Driven**: Protobuf schemas define data structure and drive table creation
- **Developer Experience**: Professional tooling with syntax highlighting, formatting, and real-time feedback
- **Extensibility**: Plugin-based architecture allows adding new engines and data sources

### 🏗️ High-Level Architecture Patterns

1. **Layered Architecture**
   - **Presentation Layer**: React web UI and CLI tools
   - **API Layer**: FastAPI with OpenAPI documentation
   - **Business Logic**: Query routing, schema management, job orchestration
   - **Data Access**: Engine-specific runners with unified interface
   - **Storage**: Multiple database engines with file-based data sources

2. **Plugin Pattern**
   - Query engines implement a common interface
   - Easy addition of new database backends
   - Schema translators convert between formats

3. **Event-Driven Operations**
   - Asynchronous query execution with status polling
   - Background job processing with real-time updates
   - Non-blocking UI with progress indicators

## System Components

### Frontend Layer
- **React Web Application**: Modern UI with Monaco editor for SQL development
- **CLI Tool (`bqlite`)**: Command-line interface for automation and CI/CD integration

### Backend Services
- **FastAPI Application**: Central API server with auto-generated documentation
- **Query Router**: Intelligent routing to appropriate execution engines
- **Schema Registry**: Protobuf schema management and versioning
- **Job Manager**: Concurrent execution control with resource management

### Execution Engines
- **DuckDB Runner**: Embedded analytics for interactive queries
- **ClickHouse Runner**: Distributed OLAP for larger datasets

### Data Management
- **Schema Translation**: Converts protobuf schemas to engine-specific DDL
- **Protobuf Ingestion**: Binary data processing and bulk loading
- **Metadata Storage**: SQLite-based registry for schemas and job history

## Key Technologies

### Frontend Stack
- **React 18**: Modern UI framework with concurrent features
- **Monaco Editor**: VS Code editor component for SQL editing
- **Axios**: HTTP client for API communication

### Backend Stack
- **Python 3.11+**: Modern Python with async/await support
- **FastAPI**: High-performance async web framework
- **Pydantic**: Data validation and serialization
- **SQLAlchemy**: Database abstraction and query building

### Database Engines
- **DuckDB**: Embedded analytical database for fast local queries
- **ClickHouse**: Distributed columnar database for scalable analytics
- **SQLite**: Lightweight metadata and configuration storage

### DevOps & Integration
- **Docker Compose**: Multi-container development environment
- **protoc**: Protocol buffer compiler for schema processing
- **Nginx**: Production-ready web server for frontend

## Deployment Modes

### Development Environment
```bash
# Frontend (React dev server)
cd frontend && npm start      # http://localhost:3000

# Backend (FastAPI with auto-reload)
cd backend && python app.py  # http://localhost:8001
```

### Production Environment
```bash
# Complete stack with Docker Compose
docker-compose up --build    # Frontend: :3000, Backend: :8001, ClickHouse: :8123
```

## Data Flow Overview

1. **Schema Registration**: Upload `.proto` files → Generate BigQuery schemas → Store metadata
2. **Table Creation**: Select engine → Translate schema to DDL → Execute table creation
3. **Data Ingestion**: Upload `.pb` files → Decode protobuf messages → Bulk insert to tables
4. **Query Execution**: Write SQL → Route to engine → Execute → Return results with metadata

## Next Steps

Explore detailed component documentation:
- **[FastAPI Backend](component-fastapi.md)** - API endpoints and request handling
- **[Query Engines](component-query-engines.md)** - DuckDB and ClickHouse integration
- **[Schema Registry](component-schema-registry.md)** - Protobuf schema management
- **[Development Environment](deployment-dev-env.md)** - Local setup and configuration
- **[System Interfaces](interfaces.md)** - Internal and external API boundaries
- **[Architecture Diagram](architecture-diagram.mmd)** - Visual system overview

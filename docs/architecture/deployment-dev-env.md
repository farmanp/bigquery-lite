# Development Environment Deployment

## Overview

BigQuery-Lite provides multiple deployment options for development environments, ranging from local development servers to fully containerized setups. This guide covers the development environment architecture, setup procedures, and configuration options.

## Development Architecture

### Local Development Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    Development Environment                   │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React Dev Server)                               │
│  ├─ Port: 3000                                             │
│  ├─ Hot Reload: Enabled                                    │
│  ├─ Proxy: localhost:8001/api                              │
│  └─ Monaco Editor: Integrated                              │
├─────────────────────────────────────────────────────────────┤
│  Backend (FastAPI with Uvicorn)                            │
│  ├─ Port: 8001                                             │
│  ├─ Auto-reload: Enabled                                   │
│  ├─ Interactive Docs: /docs, /redoc                        │
│  └─ CORS: localhost:3000                                   │
├─────────────────────────────────────────────────────────────┤
│  Database Engines                                          │
│  ├─ DuckDB: Embedded (always available)                    │
│  └─ ClickHouse: Optional (Docker container)                │
├─────────────────────────────────────────────────────────────┤
│  Storage & Data                                            │
│  ├─ SQLite: Schema registry & job history                  │
│  ├─ Parquet: Sample datasets (NYC taxi)                    │
│  └─ Protobuf: Schema definitions                           │
└─────────────────────────────────────────────────────────────┘
```

## Local Development Setup

### Prerequisites

**System Requirements:**
- **Node.js**: 16+ (for React frontend)
- **Python**: 3.11+ (for FastAPI backend)
- **protoc**: Protocol buffer compiler
- **Docker**: Optional (for ClickHouse)

**Tool Installation:**

```bash
# macOS with Homebrew
brew install node python3 protobuf

# Ubuntu/Debian
sudo apt update
sudo apt install nodejs npm python3 python3-pip protobuf-compiler

# Windows (with Chocolatey)
choco install nodejs python3 protoc
```

### Frontend Development Setup

**1. Install Dependencies**

```bash
cd frontend
npm install
```

**2. Environment Configuration**

Create `.env` file in `frontend/` directory:

```env
# Backend API URL
REACT_APP_API_BASE_URL=http://localhost:8001

# Development features
REACT_APP_DEBUG=true
REACT_APP_ENABLE_DEVTOOLS=true

# Optional: Custom branding
REACT_APP_TITLE="BigQuery-Lite Dev"
```

**3. Start Development Server**

```bash
# Standard development mode
npm start

# Alternative: Custom port
PORT=3001 npm start

# Build for production testing
npm run build
```

**Frontend Development Features:**
- **Hot Reload**: Automatic browser refresh on code changes
- **Proxy Configuration**: API calls automatically proxy to backend
- **Source Maps**: Full debugging support with original source files
- **React DevTools**: Component inspection and state debugging

### Backend Development Setup

**1. Python Environment Setup**

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

**2. Environment Configuration**

Create `.env` file in `backend/` directory:

```env
# Development mode
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# ClickHouse configuration (optional)
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=password

# Database paths
SCHEMA_REGISTRY_DB=data/schema_registry.db
JOB_HISTORY_DB=job_history.db

# Performance settings
MAX_CONCURRENT_JOBS=5
QUERY_TIMEOUT_SECONDS=300
```

**3. Start Backend Server**

```bash
# Development mode with auto-reload
python app.py

# Alternative: Using uvicorn directly
uvicorn app:app --host 0.0.0.0 --port 8001 --reload

# Production-like mode
uvicorn app:app --host 0.0.0.0 --port 8001 --workers 4
```

**Backend Development Features:**
- **Auto-reload**: Server restarts automatically on code changes
- **Interactive Documentation**: 
  - Swagger UI: http://localhost:8001/docs
  - ReDoc: http://localhost:8001/redoc
- **Debug Logging**: Detailed request/response logging
- **Health Checks**: http://localhost:8001/health

## Docker-Based Development

### Complete Stack with Docker Compose

**1. Quick Start**

```bash
# Clone repository
git clone https://github.com/farmanp/bigquery-lite.git
cd bigquery-lite

# Start all services
docker-compose up --build

# Run in background
docker-compose up --build -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

**2. Service Access Points**

| Service | URL | Purpose |
|---------|-----|---------|
| **Web Interface** | http://localhost:3000 | React frontend |
| **Backend API** | http://localhost:8001 | FastAPI backend |
| **API Documentation** | http://localhost:8001/docs | Swagger UI |
| **ClickHouse** | http://localhost:8123 | Database interface |
| **Jupyter Lab** | http://localhost:8888 | Notebook environment |

### Docker Development Workflow

**Development with Live Reload:**

```bash
# Override for development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Mount source code for live editing
docker-compose run --rm backend bash
docker-compose run --rm frontend bash
```

**Environment-Specific Configurations:**

```yaml
# docker-compose.dev.yml
services:
  backend:
    volumes:
      - ./backend:/app
      - ./data:/app/data
    environment:
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
    command: uvicorn app:app --host 0.0.0.0 --port 8001 --reload
  
  frontend:
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    environment:
      - CHOKIDAR_USEPOLLING=true  # For file watching in Docker
```

## Database Setup

### DuckDB Configuration

DuckDB runs embedded and requires no external setup:

```python
# Automatic initialization in backend
runners['duckdb'] = DuckDBRunner(db_path=":memory:")  # In-memory
# or
runners['duckdb'] = DuckDBRunner(db_path="data/bigquery_lite.db")  # Persistent
```

**Sample Data Loading:**

```bash
# Download NYC taxi dataset (optional)
mkdir -p data
curl -o data/nyc_taxi.parquet \
  "https://example.com/datasets/nyc_taxi_sample.parquet"

# DuckDB will automatically load this data on startup
```

### ClickHouse Setup

**Option 1: Docker Container (Recommended)**

```bash
# Start ClickHouse with docker-compose
docker-compose up clickhouse-server

# Manual Docker run
docker run -d \
  --name clickhouse-server \
  -p 8123:8123 \
  -p 9000:9000 \
  --ulimit nofile=262144:262144 \
  clickhouse/clickhouse-server:23.8
```

**Option 2: Local Installation**

```bash
# macOS
brew install clickhouse

# Ubuntu/Debian
sudo apt install clickhouse-server clickhouse-client

# Start service
sudo systemctl start clickhouse-server
```

**ClickHouse Configuration:**

```xml
<!-- /etc/clickhouse-server/users.xml -->
<users>
  <admin>
    <password>password</password>
    <networks incl="networks" />
    <profile>default</profile>
    <quota>default</quota>
  </admin>
</users>
```

## Port Configuration

### Default Port Assignments

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Frontend (React) | 3000 | HTTP | Web interface |
| Backend (FastAPI) | 8001 | HTTP | REST API |
| ClickHouse HTTP | 8123 | HTTP | ClickHouse web interface |
| ClickHouse Native | 9000 | TCP | ClickHouse native protocol |
| Jupyter Lab | 8888 | HTTP | Notebook environment |

### Port Conflict Resolution

**Frontend Port Conflicts:**

```bash
# Use different port
PORT=3001 npm start

# Check port availability
lsof -i :3000
netstat -tulpn | grep :3000
```

**Backend Port Conflicts:**

```bash
# Use different port
uvicorn app:app --port 8002

# Update frontend proxy in package.json
"proxy": "http://localhost:8002"
```

## Environment Variables Reference

### Frontend Environment Variables

```env
# API Configuration
REACT_APP_API_BASE_URL=http://localhost:8001
REACT_APP_WEBSOCKET_URL=ws://localhost:8001/ws

# Feature Flags
REACT_APP_ENABLE_CLICKHOUSE=true
REACT_APP_ENABLE_SCHEMA_UPLOAD=true
REACT_APP_ENABLE_PROTOBUF_INGESTION=true

# Development
REACT_APP_DEBUG=true
REACT_APP_LOG_LEVEL=debug

# UI Customization
REACT_APP_TITLE="BigQuery-Lite"
REACT_APP_THEME=light
```

### Backend Environment Variables

```env
# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG
HOST=0.0.0.0
PORT=8001

# Database Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=password

# Storage Paths
DATA_DIR=./data
SCHEMA_REGISTRY_DB=./data/schema_registry.db
JOB_HISTORY_DB=./job_history.db

# Performance
MAX_CONCURRENT_JOBS=10
QUERY_TIMEOUT_SECONDS=300
RESULT_CACHE_TTL_SECONDS=3600

# Security (for production)
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Development Tools Integration

### VS Code Configuration

**.vscode/settings.json:**

```json
{
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "python.analysis.extraPaths": ["./backend"],
  "eslint.workingDirectories": ["frontend"],
  "typescript.preferences.includePackageJsonAutoImports": "on",
  "files.exclude": {
    "**/node_modules": true,
    "**/__pycache__": true,
    "**/venv": true
  }
}
```

**.vscode/launch.json:**

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Backend Debug",
      "type": "python",
      "request": "launch",
      "program": "backend/app.py",
      "cwd": "${workspaceFolder}/backend",
      "env": {"ENVIRONMENT": "development"}
    },
    {
      "name": "Frontend Debug",
      "type": "node",
      "request": "launch",
      "cwd": "${workspaceFolder}/frontend",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["start"]
    }
  ]
}
```

### Git Hooks Setup

**pre-commit Hook:**

```bash
#!/bin/sh
# .git/hooks/pre-commit

# Frontend linting
cd frontend && npm run lint
if [ $? -ne 0 ]; then
  echo "Frontend linting failed"
  exit 1
fi

# Backend formatting
cd ../backend && python -m black . --check
if [ $? -ne 0 ]; then
  echo "Backend formatting failed"
  exit 1
fi

# Python type checking
python -m mypy app.py
```

## Troubleshooting Common Issues

### Frontend Issues

**Port Already in Use:**
```bash
# Find process using port 3000
lsof -ti:3000 | xargs kill -9

# Or use different port
PORT=3001 npm start
```

**Proxy Errors:**
```bash
# Check backend is running
curl http://localhost:8001/health

# Update proxy in package.json if needed
"proxy": "http://localhost:8001"
```

### Backend Issues

**Module Import Errors:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install missing dependencies
pip install -r requirements.txt

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Database Connection Errors:**
```bash
# Check ClickHouse is running
docker ps | grep clickhouse

# Test connection
curl http://localhost:8123

# Check environment variables
printenv | grep CLICKHOUSE
```

### Docker Issues

**Build Failures:**
```bash
# Clean build cache
docker-compose down
docker system prune -f
docker-compose build --no-cache

# Check Docker daemon
docker info
```

**Port Conflicts:**
```bash
# Check what's using ports
netstat -tulpn | grep -E ":(3000|8001|8123)"

# Stop conflicting services
docker-compose down
```

## Performance Optimization

### Development Performance Tips

**Frontend:**
- Enable React DevTools Profiler
- Use React.memo for expensive components
- Implement virtual scrolling for large result sets
- Enable service worker for caching

**Backend:**
- Use async/await consistently
- Enable query result caching
- Configure appropriate connection pools
- Use database connection reuse

**Database:**
- Use appropriate indexes for sample data
- Configure memory limits for DuckDB
- Optimize ClickHouse table engines
- Enable query profiling for performance analysis

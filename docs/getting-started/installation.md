# Installation & Quick Start

Get BigQuery-Lite up and running in under 5 minutes! This guide provides multiple installation options to suit your needs.

## Prerequisites

Choose one of the following setups:

### Option 1: Docker (Recommended)
- **Docker** and **Docker Compose** installed
- At least 4GB RAM available for containers
- Ports 3000, 8001, 8123-8125 available

### Option 2: Development Setup
- **Python 3.8+** (3.11+ recommended)
- **Node.js 16+** and **npm**
- **Git** for cloning the repository

## Quick Installation

### Docker Setup (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/farmanp/bigquery-lite.git
cd bigquery-lite

# 2. Start all services
docker-compose up --build

# 3. Wait for services to start (2-3 minutes)
# Watch for "✅ All services ready" message

# 4. Open your browser
open http://localhost:3000
```

**That's it!** You now have:
- ✅ **Web Interface** at http://localhost:3000
- ✅ **Backend API** at http://localhost:8001  
- ✅ **ClickHouse Database** at http://localhost:8123
- ✅ **Sample Data** (50k NYC taxi trips) pre-loaded
- ✅ **Jupyter Lab** at http://localhost:8888 (optional)

### Development Setup (10 minutes)

If you want to develop or modify the application:

#### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
python app.py
```

#### Frontend Setup
```bash
# In a new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

#### ClickHouse Setup (Optional)
```bash
# Start ClickHouse using Docker
docker-compose up clickhouse-server clickhouse-worker1 clickhouse-worker2
```

## Verification

### Health Checks

Test that all services are running:

```bash
# Check backend health
curl http://localhost:8001/health

# Check ClickHouse
curl http://localhost:8123/ping

# Check frontend (should return HTML)
curl http://localhost:3000
```

Expected responses:
- Backend: `{"status": "healthy", "engines": ["duckdb", "clickhouse"]}`
- ClickHouse: `Ok.`
- Frontend: HTML page content

### Your First Query

1. **Open the web interface** at http://localhost:3000
2. **Try this sample query**:
   ```sql
   SELECT 
       payment_type,
       COUNT(*) as trips,
       AVG(fare_amount) as avg_fare
   FROM nyc_taxi 
   GROUP BY payment_type 
   ORDER BY trips DESC
   LIMIT 5;
   ```
3. **Click "Run Query"** and see the results!
4. **Switch engines** - try the same query with ClickHouse

## Service Ports

| Service | Port | Purpose | URL |
|---------|------|---------|-----|
| Frontend | 3000 | Web Interface | http://localhost:3000 |
| Backend | 8001 | API Server | http://localhost:8001 |
| ClickHouse Main | 8123 | HTTP Interface | http://localhost:8123 |
| ClickHouse Worker 1 | 8124 | HTTP Interface | http://localhost:8124 |
| ClickHouse Worker 2 | 8125 | HTTP Interface | http://localhost:8125 |
| Jupyter Lab | 8888 | Notebooks | http://localhost:8888 |

## CLI Tool Installation

Install the BigQuery-Lite CLI tool for schema management:

```bash
# Install from the project directory
pip install -e .

# Verify installation
bqlite --help

# Test CLI connection
bqlite list-schemas
```

## Sample Data

BigQuery-Lite comes with a sample NYC taxi dataset (50,000 trips) for testing:

- **Table**: `nyc_taxi`
- **Format**: Parquet file
- **Size**: ~2MB (compressed)
- **Columns**: 19 columns including timestamps, fares, locations
- **Use Case**: Perfect for testing analytics queries

### Sample Data Schema
```sql
DESCRIBE nyc_taxi;
```

Key columns:
- `tpep_pickup_datetime` - Trip start time
- `tpep_dropoff_datetime` - Trip end time
- `fare_amount` - Base fare
- `total_amount` - Total amount paid
- `payment_type` - Payment method
- `trip_distance` - Distance in miles

## Environment Variables

For custom configurations, create a `.env` file:

```env
# Backend Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=password

# Resource Limits
MAX_SLOTS=8
DEFAULT_QUERY_TIMEOUT=300

# Development
DEBUG=true
LOG_LEVEL=info

# CLI Tool
BQLITE_BACKEND_URL=http://localhost:8001
```

## Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check Docker status
docker-compose ps

# View logs
docker-compose logs backend
docker-compose logs frontend
```

**Port conflicts:**
```bash
# Check what's using ports
lsof -i :3000  # Frontend
lsof -i :8001  # Backend
lsof -i :8123  # ClickHouse

# Stop conflicting services
sudo lsof -t -i:3000 | xargs kill -9
```

**Reset everything:**
```bash
# Stop and remove all containers/data
docker-compose down -v

# Start fresh
docker-compose up --build
```

**Memory issues:**
```bash
# Check Docker memory allocation
docker stats

# Increase Docker memory limit to 4GB+
# (Docker Desktop -> Settings -> Resources)
```

### Getting Help

- **Documentation**: See the [full documentation](../README.md)
- **API Docs**: Visit http://localhost:8001/docs for interactive API documentation
- **Issues**: [Open an issue](https://github.com/farmanp/bigquery-lite/issues) on GitHub
- **Discussions**: Use GitHub Discussions for questions and ideas

## Next Steps

Now that you have BigQuery-Lite running:

1. **[Try Sample Queries](sample-queries.md)** - Explore the data with pre-built queries
2. **[Learn the Interface](../user-guide/web-interface.md)** - Master the web interface features
3. **[Use the CLI](../user-guide/cli-tool.md)** - Learn command-line operations
4. **[Load Your Data](../user-guide/data-management.md)** - Import your own datasets
5. **[Compare Engines](../architecture/engines.md)** - Understand DuckDB vs ClickHouse

**Happy querying!** 🎉
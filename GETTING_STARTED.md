# 🚀 Getting Started with BigQuery-Lite

A quick start guide to get you up and running with BigQuery-Lite in under 5 minutes!

## Prerequisites

- **Docker & Docker Compose** (recommended)
- **OR** Python 3.11+ and Node.js 18+ for development setup

## ⚡ Quick Start (Docker)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd bigquery-lite

# 2. Start all services with one command
docker-compose up --build

# 3. Open your browser
open http://localhost:3000
```

That's it! You now have:
- ✅ **Web Interface** at http://localhost:3000
- ✅ **Backend API** at http://localhost:8001  
- ✅ **ClickHouse Database** at http://localhost:8123
- ✅ **Sample Data** (50k NYC taxi trips) pre-loaded

## 🎯 Your First Query

1. **Open the web interface** at http://localhost:3000
2. **Try this sample query**:
   ```sql
   SELECT 
       payment_type,
       COUNT(*) as trips,
       AVG(fare_amount) as avg_fare
   FROM nyc_taxi 
   GROUP BY payment_type 
   ORDER BY trips DESC;
   ```
3. **Click "Run Query"** and see the results!
4. **Switch engines** - try the same query with ClickHouse

## 🔧 Development Setup (Optional)

If you want to develop or modify the application:

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

### ClickHouse (Docker)
```bash
docker-compose up clickhouse-server
```

## 📊 Sample Queries to Try

### Basic Exploration
```sql
-- Count total trips
SELECT COUNT(*) as total_trips FROM nyc_taxi;

-- Average fare by payment type
SELECT payment_type, AVG(fare_amount) as avg_fare 
FROM nyc_taxi 
GROUP BY payment_type;
```

### Time Series Analysis
```sql
-- Trips by hour of day
SELECT 
    EXTRACT(hour FROM tpep_pickup_datetime) as hour,
    COUNT(*) as trips
FROM nyc_taxi 
GROUP BY hour 
ORDER BY hour;
```

### Advanced Analytics
```sql
-- Moving averages
WITH daily_trips AS (
    SELECT 
        DATE(tpep_pickup_datetime) as date,
        COUNT(*) as trips
    FROM nyc_taxi 
    GROUP BY date
)
SELECT 
    date,
    trips,
    AVG(trips) OVER (
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as weekly_avg
FROM daily_trips 
ORDER BY date;
```

## 🎨 Interface Features

- **Monaco Editor**: Professional SQL editor with syntax highlighting
- **Engine Selection**: Switch between DuckDB and ClickHouse
- **Real-time Results**: Live query execution with progress updates
- **Query Plans**: Detailed execution analysis
- **Job History**: Track all your previous queries
- **Performance Metrics**: Execution time and resource usage

## 🐛 Troubleshooting

### Services Won't Start
```bash
# Check Docker status
docker-compose ps

# View logs
docker-compose logs backend
docker-compose logs frontend
```

### Port Already in Use
```bash
# Stop any existing services
docker-compose down

# Check what's using ports
lsof -i :3000  # Frontend
lsof -i :8001  # Backend
lsof -i :8123  # ClickHouse
```

### Reset Everything
```bash
# Stop and remove all containers/data
docker-compose down -v

# Start fresh
docker-compose up --build
```

## 🔗 API Testing

Test the backend API directly:

```bash
# Submit a query
curl -X POST "http://localhost:8001/queries" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) FROM nyc_taxi", "engine": "duckdb"}'

# Check system status
curl "http://localhost:8001/status"
```

## 📚 Next Steps

1. **Explore the sample data** with different queries
2. **Compare DuckDB vs ClickHouse** performance
3. **Try advanced SQL features** like window functions
4. **Load your own data** (Parquet or CSV files)
5. **Build custom analytics** for your use case

## 🆘 Need Help?

- 📖 **Full Documentation**: See [README.md](README.md)
- 🐳 **Docker Guide**: See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)
- 🐛 **Issues**: [Open an issue](https://github.com/your-username/bigquery-lite/issues)

**Happy querying!** 🎉
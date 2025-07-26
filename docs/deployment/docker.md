# Docker Deployment Guide

This guide covers deploying BigQuery-Lite using Docker and Docker Compose for development and production environments.

## Quick Start

### Complete Stack Deployment

```bash
# Clone the repository
git clone https://github.com/farmanp/bigquery-lite.git
cd bigquery-lite

# Start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

**Access Points:**
- **Web Interface**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **ClickHouse**: http://localhost:8123
- **Jupyter Lab**: http://localhost:8888

## Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │    │   Backend   │    │ ClickHouse  │
│   (React)   │───▶│  (FastAPI)  │───▶│   Cluster   │
│   Port 3000 │    │  Port 8001  │    │  Port 8123  │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   ▼                   │
       │            ┌─────────────┐            │
       │            │   DuckDB    │            │
       └────────────│ (Embedded)  │────────────┘
                    └─────────────┘
```

## Service Configuration

### Port Mapping

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| Frontend | 80 | 3000 | Web interface |
| Backend | 8001 | 8001 | API server |
| ClickHouse Coordinator | 8123 | 8123 | HTTP interface |
| ClickHouse Worker 1 | 8123 | 8124 | HTTP interface |
| ClickHouse Worker 2 | 8123 | 8125 | HTTP interface |
| Jupyter | 8888 | 8888 | Notebook interface |

### Environment Variables

The system uses these environment variables:

**Backend Configuration:**
```env
ENVIRONMENT=docker
CLICKHOUSE_HOST=clickhouse-server
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=password
```

**Frontend Configuration:**
```env
NODE_ENV=production
REACT_APP_API_BASE_URL=/api
```

## Volume Management

### Persistent Data

Data is stored in Docker volumes:
- `clickhouse_data` - ClickHouse coordinator data
- `clickhouse_worker1_data` - Worker 1 data
- `clickhouse_worker2_data` - Worker 2 data
- `backend_db` - Backend database and job history

### Shared Directories

- `./data:/app/data` - Sample datasets and shared files
- `./notebooks:/home/jovyan/work/notebooks` - Jupyter notebooks

## Selective Service Deployment

### Backend and Database Only

For local frontend development:

```bash
# Start only backend services
docker-compose up backend clickhouse-server clickhouse-worker1 clickhouse-worker2

# In another terminal, run frontend locally
cd frontend
npm start
```

### Database Cluster Only

To use external backend:

```bash
# Start only ClickHouse cluster
docker-compose up clickhouse-server clickhouse-worker1 clickhouse-worker2
```

### Development Mode

```bash
# Start with hot reload (if volumes are mounted)
docker-compose up --build

# View logs for specific service
docker-compose logs -f backend
```

## Health Checks and Monitoring

### Service Health

Check that all services are running:

```bash
# Check service status
docker-compose ps

# Check backend health
curl http://localhost:8001/health

# Check ClickHouse
curl http://localhost:8123/ping

# Check frontend
curl http://localhost:3000
```

### Log Monitoring

```bash
# View all logs
docker-compose logs

# Follow specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f clickhouse-server

# View recent logs
docker-compose logs --tail=50 backend
```

### Resource Usage

```bash
# Monitor resource usage
docker stats

# Check specific containers
docker stats bigquery-lite-frontend bigquery-lite-backend
```

## Data Management

### Backup Operations

```bash
# Backup ClickHouse data
docker run --rm \
  -v bigquery-lite_clickhouse_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/clickhouse_backup.tar.gz -C /data .

# Backup all volumes
docker run --rm \
  -v bigquery-lite_backend_db:/backend_db \
  -v bigquery-lite_clickhouse_data:/clickhouse_data \
  -v $(pwd):/backup \
  alpine sh -c "
    tar czf /backup/backend_backup.tar.gz -C /backend_db . &&
    tar czf /backup/clickhouse_backup.tar.gz -C /clickhouse_data .
  "
```

### Restore Operations

```bash
# Restore ClickHouse data
docker run --rm \
  -v bigquery-lite_clickhouse_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/clickhouse_backup.tar.gz -C /data
```

### Reset All Data

```bash
# Stop services and remove volumes (CAUTION: This deletes all data)
docker-compose down -v

# Start fresh
docker-compose up --build
```

## Scaling and Performance

### Horizontal Scaling

```bash
# Scale ClickHouse workers
docker-compose up --scale clickhouse-worker1=2 --scale clickhouse-worker2=2

# Scale backend (requires load balancer configuration)
docker-compose up --scale backend=2
```

### Resource Limits

Add resource limits to `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    
  clickhouse-server:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

### Performance Optimization

1. **Memory Allocation**
   - Increase Docker memory limit to 8GB+
   - Allocate sufficient memory to ClickHouse containers

2. **CPU Usage**
   - Use multi-core systems for better performance
   - Adjust CPU limits based on workload

3. **Storage**
   - Use SSD storage for better I/O performance
   - Consider separate volumes for data and logs

## Networking

### Internal Communication

Services communicate via the `bigquery-net` Docker network:
- Frontend → Backend: HTTP requests via nginx proxy
- Backend → ClickHouse: Direct connection using service names
- Backend → DuckDB: Embedded (no network)

### External Access

Configure external access for production:

```yaml
# Example nginx configuration for external access
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
```

## Troubleshooting

### Common Issues

**1. Port Conflicts**

```bash
# Check what's using ports
lsof -i :3000
lsof -i :8001
lsof -i :8123

# Stop conflicting services
sudo lsof -t -i:3000 | xargs kill -9
```

**2. Build Failures**

```bash
# Clean Docker cache
docker system prune -f
docker builder prune -f

# Rebuild from scratch
docker-compose build --no-cache
```

**3. Memory Issues**

```bash
# Check available memory
docker system df

# Increase Docker memory limit in Docker Desktop
# Settings → Resources → Memory → 8GB+
```

**4. Service Connection Issues**

```bash
# Test internal connectivity
docker-compose exec backend ping clickhouse-server
docker-compose exec frontend wget -qO- http://backend:8001/health

# Check network configuration
docker network inspect bigquery-lite_bigquery-net
```

### Health Check Failures

```bash
# Check backend health manually
docker-compose exec backend python -c "
import requests
response = requests.get('http://localhost:8001/health')
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
"

# Restart unhealthy services
docker-compose restart backend
docker-compose restart clickhouse-server
```

## Production Considerations

### Security

1. **Change Default Passwords**
   ```env
   CLICKHOUSE_PASSWORD=your_secure_password_here
   ```

2. **Use HTTPS**
   - Configure SSL certificates
   - Use reverse proxy with SSL termination

3. **Network Security**
   - Restrict port access to necessary services only
   - Use internal networks for service communication

### Monitoring

1. **Log Aggregation**
   - Use centralized logging (ELK stack, Fluentd)
   - Configure log rotation

2. **Metrics Collection**
   - Add Prometheus monitoring
   - Set up Grafana dashboards

3. **Alerting**
   - Monitor service health
   - Alert on high resource usage

### Backup Strategy

1. **Regular Backups**
   - Schedule automated backups
   - Test restore procedures

2. **Multiple Backup Locations**
   - Local and remote backup storage
   - Version backup files

### High Availability

1. **Load Balancing**
   - Multiple frontend instances
   - Backend load balancing

2. **Database Clustering**
   - ClickHouse cluster configuration
   - Data replication

## Docker Compose Reference

### Complete docker-compose.yml

The system includes these services:

```yaml
services:
  frontend:    # React app with Nginx
  backend:     # FastAPI server
  clickhouse-server:   # Main ClickHouse coordinator
  clickhouse-worker1:  # Worker node 1
  clickhouse-worker2:  # Worker node 2
  jupyter:     # Optional Jupyter Lab
```

### Custom Configuration

Create `docker-compose.override.yml` for custom settings:

```yaml
version: '3.8'
services:
  backend:
    environment:
      - DEBUG=true
      - LOG_LEVEL=debug
    volumes:
      - ./custom_data:/app/custom_data
  
  clickhouse-server:
    environment:
      - CLICKHOUSE_PASSWORD=my_secure_password
```

## Next Steps

- **[Development Setup](development.md)** - Local development environment
- **[Configuration Guide](configuration.md)** - Environment configuration
- **[Monitoring Setup](monitoring.md)** - Logging and monitoring
- **[Troubleshooting](../advanced/troubleshooting.md)** - Common issues and solutions
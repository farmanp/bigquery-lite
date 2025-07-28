# 🐳 Docker Deployment Guide

ide covers deploying BigQuery-Lite using Docker and Docker Compose.

## 🚀 Quick Start (Full Docker Setup)

### Option 1: Complete Stack
```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

**Access Points:**
- **Web Interface**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **ClickHouse**: http://localhost:8123
- **Jupyter Lab**: http://localhost:8888

### Option 2: Selective Services
```bash
# Start only ClickHouse cluster
docker-compose up clickhouse-server clickhouse-worker1 clickhouse-worker2

# Start backend only (for local frontend development)
docker-compose up backend clickhouse-server

# Start everything except Jupyter
docker-compose up frontend backend clickhouse-server clickhouse-worker1 clickhouse-worker2
```

## 🏗️ Architecture

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

## 🔧 Configuration

### Environment Variables

The Docker setup uses environment variables for configuration:

**Backend (.env.docker):**
```env
ENVIRONMENT=docker
CLICKHOUSE_HOST=clickhouse-server
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=password
```

**Frontend:**
```env
REACT_APP_API_BASE_URL=/api
NODE_ENV=production
```

### Volume Mounts

- `./data:/app/data` - Shared data directory (NYC taxi dataset)
- `backend_db:/app/db` - Backend database persistence
- `clickhouse_data:/var/lib/clickhouse` - ClickHouse data persistence

## 🌐 Networking

### Service Communication

Services communicate via the `bigquery-net` Docker network:

- **Frontend** → **Backend**: HTTP requests via nginx proxy
- **Backend** → **ClickHouse**: Direct connection using service names
- **Backend** → **DuckDB**: Embedded (no network)

### Port Mapping

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| Frontend | 80 | 3000 | Web interface |
| Backend | 8001 | 8001 | API server |
| ClickHouse Coordinator | 8123 | 8123 | HTTP interface |
| ClickHouse Worker 1 | 8123 | 8124 | HTTP interface |
| ClickHouse Worker 2 | 8123 | 8125 | HTTP interface |
| Jupyter | 8888 | 8888 | Notebook interface |

## 📁 Docker Images

### Frontend Image (Multi-stage Build)
```dockerfile
# Build stage
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY src/ src/
COPY public/ public/
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Backend Image
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
```

## 🔄 Development Workflow

### Local Development with Docker Backend

```bash
# Start only backend services
docker-compose up backend clickhouse-server -d

# Run frontend locally
cd frontend
npm start

# Frontend at localhost:3000, Backend in Docker
```

### Hot Reload Development

```bash
# Frontend with hot reload
cd frontend
npm start

# Backend with hot reload (if mounted as volume)
docker-compose up backend --build
```

### Building Images

```bash
# Build specific service
docker-compose build frontend
docker-compose build backend

# Build all services
docker-compose build

# Force rebuild without cache
docker-compose build --no-cache
```

## 📊 Monitoring and Logs

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs frontend
docker-compose logs backend
docker-compose logs clickhouse-server

# Follow logs in real-time
docker-compose logs -f backend
```

### Health Checks

The backend includes health checks:
```bash
# Check backend health
curl http://localhost:8001/health

# Docker health status
docker-compose ps
```

### Resource Usage
```bash
# Check resource usage
docker stats

# Service-specific stats
docker stats bigquery-lite-frontend bigquery-lite-backend
```

## 🗄️ Data Management

### Persistent Data

Data is persisted in Docker volumes:
- **ClickHouse data**: `clickhouse_data`, `clickhouse_worker1_data`, `clickhouse_worker2_data`
- **Backend database**: `backend_db`
- **Sample data**: Mounted from `./data` directory

### Backup and Restore

```bash
# Backup volumes
docker run --rm -v bigquery-lite_clickhouse_data:/data -v $(pwd):/backup alpine tar czf /backup/clickhouse_backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v bigquery-lite_clickhouse_data:/data -v $(pwd):/backup alpine tar xzf /backup/clickhouse_backup.tar.gz -C /data
```

### Reset Data

```bash
# Stop services
docker-compose down

# Remove volumes (CAUTION: This deletes all data)
docker-compose down -v

# Start fresh
docker-compose up --build
```

## 🐛 Troubleshooting

### Common Issues

**1. Port Conflicts**
```bash
# Check what's using ports
lsof -i :3000
lsof -i :8001
lsof -i :8123

# Use different ports
docker-compose up --scale frontend=0  # Skip frontend
# Or edit docker-compose.yml port mappings
```

**2. Build Failures**
```bash
# Clean Docker cache
docker system prune -f
docker builder prune -f

# Rebuild from scratch
docker-compose build --no-cache
```

**3. Service Connection Issues**
```bash
# Check network connectivity
docker-compose exec backend ping clickhouse-server
docker-compose exec frontend ping backend

# Check service status
docker-compose ps
docker-compose logs backend
```

**4. Frontend API Connection**
```bash
# Check if backend is accessible from frontend
docker-compose exec frontend wget -O- http://backend:8001/health

# Check nginx proxy configuration
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf
```

### Performance Optimization

**1. Resource Limits**
```yaml
# Add to docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          memory: 512M
```

**2. Multi-stage Builds**
- Frontend uses multi-stage build to minimize image size
- Only production dependencies included in final image

**3. Caching**
```bash
# Use BuildKit for better caching
DOCKER_BUILDKIT=1 docker-compose build
```

## 🚀 Production Deployment

### Production Considerations

1. **Environment Variables**
   - Use secrets management for passwords
   - Set appropriate resource limits
   - Configure proper logging

2. **Security**
   - Change default passwords
   - Use HTTPS with SSL certificates
   - Implement authentication if needed

3. **Scaling**
   - Add more ClickHouse workers
   - Use load balancers for frontend
   - Implement horizontal pod autoscaling

### Docker Swarm / Kubernetes

```bash
# Docker Swarm deployment
docker stack deploy -c docker-compose.yml bigquery-lite

# Kubernetes (requires conversion)
kompose convert
kubectl apply -f .
```

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale ClickHouse workers
docker-compose up --scale clickhouse-worker1=2 --scale clickhouse-worker2=2

# Scale backend (requires load balancer)
docker-compose up --scale backend=3
```

### Vertical Scaling

Update resource limits in docker-compose.yml:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

---

This Docker setup provides a complete, production-ready deployment of BigQuery-Lite that can be easily scaled and maintained! 🎉

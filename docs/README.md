# BigQuery-Lite Documentation

Welcome to the BigQuery-Lite documentation! This documentation provides comprehensive guides for installation, usage, development, and deployment of BigQuery-Lite.

## Quick Navigation

### Getting Started
- [Installation & Quick Start](getting-started/installation.md) - Get up and running in 5 minutes
- [First Query Tutorial](getting-started/first-query.md) - Your first BigQuery-Lite query
- [Sample Queries](getting-started/sample-queries.md) - Example queries to explore

### User Guides
- [Web Interface Guide](user-guide/web-interface.md) - Using the React frontend
- [CLI Tool Guide](user-guide/cli-tool.md) - Command-line interface documentation
- [Query Writing](user-guide/query-writing.md) - SQL syntax and best practices
- [Data Management](user-guide/data-management.md) - Loading and managing data

### API Reference
- [REST API](api/rest-api.md) - Complete API documentation
- [Query Endpoints](api/queries.md) - Query execution and management
- [Schema Endpoints](api/schemas.md) - Schema registration and management
- [Data Ingestion](api/ingestion.md) - Protobuf data ingestion APIs

### Architecture & Development
- [System Architecture](architecture/overview.md) - High-level system design
- [Backend Architecture](architecture/backend.md) - FastAPI backend details
- [Frontend Architecture](architecture/frontend.md) - React frontend details
- [Database Engines](architecture/engines.md) - DuckDB and ClickHouse integration

### Deployment
- [Docker Deployment](deployment/docker.md) - Production Docker deployment
- [Development Setup](deployment/development.md) - Local development environment
- [Configuration](deployment/configuration.md) - Environment and configuration options
- [Monitoring](deployment/monitoring.md) - Logging and monitoring setup

### Advanced Topics
- [Protobuf Integration](advanced/protobuf-integration.md) - Schema management with Protocol Buffers
- [Performance Optimization](advanced/performance.md) - Tuning for optimal performance
- [Security](advanced/security.md) - Security considerations and best practices
- [Troubleshooting](advanced/troubleshooting.md) - Common issues and solutions

### Contributing
- [Development Guide](contributing/development.md) - Setting up development environment
- [Code Standards](contributing/code-standards.md) - Coding conventions and standards
- [Testing](contributing/testing.md) - Testing guidelines and setup
- [Contributing](contributing/contributing.md) - How to contribute to the project

## Quick Links

- **Main Repository**: [BigQuery-Lite on GitHub](https://github.com/farmanp/bigquery-lite)
- **Web Interface**: http://localhost:3000 (after installation)
- **API Documentation**: http://localhost:8001/docs (FastAPI interactive docs)
- **Issues & Support**: [GitHub Issues](https://github.com/farmanp/bigquery-lite/issues)

## Project Overview

BigQuery-Lite is a powerful local BigQuery-like analytics environment that combines:

- **DuckDB** for lightning-fast embedded analytics
- **ClickHouse** for distributed OLAP processing  
- **React Web Interface** with BigQuery-inspired design
- **FastAPI Backend** with async processing
- **Protobuf Schema Management** for type-safe data modeling
- **Slot-based Resource Management** simulating BigQuery's execution model

Perfect for development, testing, and local analytics without cloud dependencies!

---

*This documentation is maintained alongside the codebase. If you find any issues or have suggestions for improvement, please [open an issue](https://github.com/farmanp/bigquery-lite/issues) or submit a pull request.*
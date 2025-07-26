# ADR-0001: Dual Engine Architecture (DuckDB + ClickHouse)

## Status

Accepted

## Context

BigQuery-Lite needs to provide local analytics capabilities that simulate Google BigQuery's functionality. We need to choose appropriate database engines that can handle both:

1. **Embedded Analytics**: Fast, in-memory processing for development and small-to-medium datasets
2. **Distributed Processing**: Scalable, production-ready analytics for larger datasets

The solution should provide a consistent interface while leveraging the strengths of different engines.

## Decision

We will implement a **dual engine architecture** using:

- **DuckDB** as the embedded analytics engine
- **ClickHouse** as the distributed OLAP engine

Both engines will be accessible through a unified FastAPI backend with identical SQL interfaces.

## Rationale

### DuckDB Selection

**Advantages:**
- Zero-configuration embedded database
- Excellent performance for analytical workloads up to ~1GB datasets
- Native Python integration
- Advanced SQL features (window functions, CTEs, JSON processing)
- Parquet file format support
- Perfect for development and prototyping

**Use Cases:**
- Local development environment
- Data exploration and prototyping
- Small to medium dataset analytics
- Single-user scenarios

### ClickHouse Selection

**Advantages:**
- Columnar storage optimized for analytics
- Horizontal scaling capabilities
- Excellent compression and query performance
- SQL interface with BigQuery-like features
- Production-ready distributed architecture
- Real-time analytics capabilities

**Use Cases:**
- Production deployments
- Large dataset processing (>1GB)
- Multi-user concurrent access
- Real-time analytics dashboards

### Unified Interface Benefits

1. **Development Flexibility**: Start with DuckDB for prototyping, scale to ClickHouse for production
2. **Performance Comparison**: Benchmark queries across both engines
3. **Migration Path**: Seamless transition between engines as data grows
4. **Learning Platform**: Compare embedded vs distributed analytics approaches

## Implementation Details

### Backend Architecture

```python
# Abstract base class for database runners
class BaseRunner:
    async def execute_query(self, sql: str) -> QueryResult
    async def get_schemas(self) -> List[Schema]
    async def health_check(self) -> bool

# Engine-specific implementations
class DuckDBRunner(BaseRunner):
    # Embedded execution logic

class ClickHouseRunner(BaseRunner):
    # Distributed execution logic
```

### API Design

```http
POST /queries
{
  "sql": "SELECT COUNT(*) FROM table",
  "engine": "duckdb" | "clickhouse"
}
```

### Frontend Integration

- Engine selector in the UI
- Performance comparison views
- Engine-specific query plans and metrics

## Consequences

### Positive

- **Flexibility**: Appropriate engine selection based on use case
- **Scalability**: Clear upgrade path from embedded to distributed
- **Performance**: Optimized execution for different data sizes
- **Learning Value**: Demonstrates both embedded and distributed analytics

### Negative

- **Complexity**: Maintain two different database integrations
- **Data Synchronization**: Need mechanisms to sync data between engines
- **Testing Overhead**: Ensure feature parity across both engines

### Risks and Mitigations

**Risk**: Feature divergence between engines
**Mitigation**: Standardized SQL subset, comprehensive test suite

**Risk**: Data consistency issues
**Mitigation**: Clear data loading procedures, schema validation

**Risk**: Increased maintenance burden
**Mitigation**: Abstract base classes, shared utilities

## Alternatives Considered

### Single Engine Options

1. **DuckDB Only**: Simple but limited scalability
2. **ClickHouse Only**: Complex setup for development environments
3. **PostgreSQL**: Good general-purpose DB but not optimized for analytics

### Other Dual Engine Combinations

1. **DuckDB + PostgreSQL**: Limited analytics performance in PostgreSQL
2. **SQLite + ClickHouse**: SQLite not optimized for analytics workloads

## Related Decisions

- [ADR-0002: FastAPI Backend Framework](0002-fastapi-backend-framework.md)
- [ADR-0003: Slot-Based Query Scheduling](0003-slot-based-query-scheduling.md)

## References

- [DuckDB Documentation](https://duckdb.org/docs/)
- [ClickHouse Documentation](https://clickhouse.com/docs/)
- [BigQuery Architecture Patterns](https://cloud.google.com/bigquery/docs/introduction)

---

**Date**: 2024-01-26  
**Author**: Development Team  
**Reviewers**: Architecture Team
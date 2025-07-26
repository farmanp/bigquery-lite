# CLI Tool Guide

The BigQuery-Lite CLI tool (`bqlite`) provides powerful command-line operations for schema management, data ingestion, and backend interaction. This guide covers installation, configuration, and usage.

## Installation

### From Project Directory
```bash
# Install in development mode
pip install -e .

# Verify installation
bqlite --help
```

### From PyPI (when available)
```bash
pip install bqlite
```

### Requirements
- Python 3.8+
- Access to BigQuery-Lite backend (default: http://localhost:8001)

## Configuration

### Backend URL

Set the backend URL using environment variable:
```bash
export BQLITE_BACKEND_URL=http://localhost:8001
```

Or use the `--backend-url` flag with each command:
```bash
bqlite list-schemas --backend-url http://my-backend:8001
```

### Default Configuration
- **Backend URL**: http://localhost:8002 (note: default differs from docs, adjust as needed)
- **Timeout**: 30 seconds for most operations, 300 seconds for data ingestion
- **Output Format**: Rich formatted tables and colored output

## Commands Overview

| Command | Purpose | Example |
|---------|---------|---------|
| `register` | Register protobuf schema | `bqlite register schema.proto --table users` |
| `create-table` | Create tables from schema | `bqlite create-table users --engines duckdb,clickhouse` |
| `ingest` | Ingest protobuf data | `bqlite ingest data.pb --schema users` |
| `list-schemas` | List registered schemas | `bqlite list-schemas` |

## Schema Management

### Register a Protobuf Schema

Register a `.proto` file to create table schemas:

```bash
# Basic registration
bqlite register user_events.proto --table user_events

# With custom database
bqlite register user_events.proto --table user_events --database analytics

# Full example
bqlite register schemas/user_events.proto \
    --table user_events \
    --database bigquery_lite \
    --backend-url http://localhost:8001
```

**Example output:**
```
✅ Schema registered successfully!
Schema ID: a1b2c3d4
Table: bigquery_lite.user_events  
Fields: 8
Version: a1b2c3d4
```

### List Registered Schemas

View all schemas in the registry:

```bash
bqlite list-schemas
```

**Example output:**
```
┌─────────────┬─────────────┬──────────────┬────────┬──────────┬───────────┐
│ Schema ID   │ Table       │ Database     │ Fields │ Versions │ Created   │
├─────────────┼─────────────┼──────────────┼────────┼──────────┼───────────┤
│ a1b2c3d4... │ user_events │ bigquery_lite│ 8      │ 1        │ 2024-01-15│
│ b2c3d4e5... │ products    │ ecommerce    │ 12     │ 2        │ 2024-01-14│
└─────────────┴─────────────┴──────────────┴────────┴──────────┴───────────┘
```

## Table Creation

### Create Tables from Registered Schemas

Create actual database tables from registered protobuf schemas:

```bash
# Create in DuckDB only (default)
bqlite create-table user_events

# Create in multiple engines
bqlite create-table user_events --engines duckdb,clickhouse

# With custom options
bqlite create-table user_events \
    --engines duckdb,clickhouse \
    --database analytics \
    --flattened-view \
    --replace
```

**Options:**
- `--engines`: Comma-separated list of engines (`duckdb`, `clickhouse`)
- `--database`: Target database name (default: `bigquery_lite`)
- `--if-not-exists`: Use IF NOT EXISTS clause (default: true)
- `--replace`: Replace existing tables (sets `--if-not-exists` to false)
- `--flattened-view`: Create flattened view for nested schemas

**Example output:**
```
✅ Table creation completed!

Table Creation Results: user_events
┌───────────┬───────────┬────────────────┬─────────┐
│ Engine    │ Status    │ Execution Time │ Error   │
├───────────┼───────────┼────────────────┼─────────┤
│ duckdb    │ ✅ Success│ 0.023s         │         │
│ clickhouse│ ✅ Success│ 0.156s         │         │
└───────────┴───────────┴────────────────┴─────────┘

📊 Flattened view created for nested schema

Summary: 2/2 engines successful
```

## Data Ingestion

### Ingest Protobuf Data

Load protobuf binary data into tables:

```bash
# Basic ingestion
bqlite ingest data/user_events.pb --schema user_events

# With custom options
bqlite ingest data/user_events.pb \
    --schema user_events \
    --engine clickhouse \
    --database analytics \
    --batch-size 5000 \
    --no-create-table
```

**Options:**
- `--schema`: Schema name (table name) that data conforms to
- `--engine`: Target engine (`duckdb` or `clickhouse`, default: `duckdb`)
- `--database`: Target database (default: `bigquery_lite`)
- `--batch-size`: Records per batch (default: 1000)
- `--create-table/--no-create-table`: Create table if not exists (default: true)

**Example output:**
```
🔄 Ingesting data from user_events.pb...
✅ Data ingestion completed successfully!
Job ID: job_789xyz
Records processed: 50000
Records inserted: 50000
Processing time: 2.456s
```

**With errors:**
```
⚠️ Data ingestion partially successful
Job ID: job_789xyz
Records processed: 50000
Records inserted: 49997
Processing time: 2.456s

Errors encountered: 3
  1. Invalid timestamp format in record 1234
  2. Missing required field 'user_id' in record 5678
  3. Value out of range for field 'age' in record 9012
```

## Advanced Usage

### Schema Workflow Example

Complete workflow from protobuf definition to data ingestion:

```bash
# 1. Define schema in protobuf
cat > schemas/user_events.proto << EOF
syntax = "proto3";
package events;

import "gen_bq_schema/bq_table.proto";
import "gen_bq_schema/bq_field.proto";

message UserEvent {
  option (gen_bq_schema.bigquery_opts).table_name = "user_events";
  
  int64 event_id = 1 [(gen_bq_schema.bigquery).require = true];
  string user_id = 2 [(gen_bq_schema.bigquery).require = true];
  string event_type = 3;
  google.protobuf.Timestamp timestamp = 4;
  UserProfile profile = 5;
  
  message UserProfile {
    string name = 1;
    int32 age = 2;
    repeated string interests = 3;
  }
}
EOF

# 2. Register the schema
bqlite register schemas/user_events.proto --table user_events

# 3. Create tables in both engines
bqlite create-table user_events --engines duckdb,clickhouse --flattened-view

# 4. Ingest sample data
bqlite ingest data/sample_user_events.pb --schema user_events --engine duckdb

# 5. Verify data loaded
curl -X POST "http://localhost:8001/queries" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) FROM user_events", "engine": "duckdb"}'
```

### Batch Operations

Process multiple schemas or data files:

```bash
# Register multiple schemas
for proto in schemas/*.proto; do
    table_name=$(basename "$proto" .proto)
    bqlite register "$proto" --table "$table_name"
done

# Create tables for all registered schemas
bqlite list-schemas --format json | jq -r '.schemas[].table_name' | while read table; do
    bqlite create-table "$table" --engines duckdb,clickhouse
done

# Ingest multiple data files
for pb_file in data/*.pb; do
    schema_name=$(basename "$pb_file" .pb)
    bqlite ingest "$pb_file" --schema "$schema_name"
done
```

## Error Handling

### Common Errors and Solutions

**Connection Error:**
```
Error: Cannot connect to backend at http://localhost:8001
Make sure the backend service is running.
```
*Solution:* Start the backend service or check the URL

**Schema Not Found:**
```
Error: No registered schema found for table 'bigquery_lite.user_events'
Use 'bqlite list-schemas' to see available schemas.
```
*Solution:* Register the schema first or check the table name

**File Not Found:**
```
Error: Proto file not found: schemas/missing.proto
```
*Solution:* Check the file path and ensure the file exists

**Validation Error:**
```
Validation Error: Field 'user_id' is required but missing
```
*Solution:* Check your protobuf definition and data format

### Debugging

Enable verbose output for debugging:

```bash
# Set environment variable for detailed logging
export BQLITE_DEBUG=true

# Or use Python logging
export PYTHONPATH=. python -m bqlite.cli list-schemas
```

## Integration with Backend

### API Compatibility

The CLI tool uses the same REST API as the web interface:

| CLI Command | API Endpoint | Method |
|-------------|--------------|---------|
| `register` | `/schemas/register` | POST |
| `create-table` | `/schemas/{id}/tables/create` | POST |
| `ingest` | `/schemas/{id}/ingest` | POST |
| `list-schemas` | `/schemas` | GET |

### Authentication (Future)

When authentication is implemented:

```bash
# Set API token
export BQLITE_API_TOKEN=your_token_here

# Or use config file
mkdir -p ~/.config/bqlite
echo "api_token: your_token_here" > ~/.config/bqlite/config.yaml
```

## Best Practices

### Schema Management
1. **Use semantic versioning** in your protobuf schemas
2. **Test schema changes** with small datasets first
3. **Keep protobuf files in version control**
4. **Use consistent naming conventions** for tables and databases

### Data Ingestion
1. **Start with small batch sizes** for testing
2. **Monitor memory usage** during large ingestions
3. **Use appropriate engines** (DuckDB for development, ClickHouse for production)
4. **Validate data quality** before ingestion

### Performance Tips
1. **Use flattened views** for complex nested schemas when querying frequently
2. **Batch multiple operations** instead of single calls
3. **Choose the right engine** for your query patterns
4. **Monitor backend logs** for performance insights

## Configuration File

Create a configuration file for common settings:

```yaml
# ~/.config/bqlite/config.yaml
backend_url: http://localhost:8001
default_database: bigquery_lite
default_engine: duckdb
batch_size: 1000
timeout: 30
```

*Note: Configuration file support is planned for future versions*

## Next Steps

- **[API Reference](../api/schemas.md)** - Detailed API documentation
- **[Protobuf Integration](../advanced/protobuf-integration.md)** - Advanced schema management
- **[Data Management](data-management.md)** - Loading and managing data
- **[Troubleshooting](../advanced/troubleshooting.md)** - Common issues and solutions
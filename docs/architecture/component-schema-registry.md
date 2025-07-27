# Schema Registry Architecture

## Overview

The Schema Registry is the **central schema management system** that handles protobuf schema registration, versioning, and metadata storage. It integrates with `protoc-gen-bq-schema` to convert `.proto` files into BigQuery-compatible schemas, then provides translation services to generate engine-specific DDL statements for table creation.

## Core Responsibilities

1. **Schema Storage**: Version and store protobuf schemas with metadata
2. **BigQuery Translation**: Convert `.proto` files to BigQuery JSON schemas
3. **DDL Generation**: Translate schemas to engine-specific SQL DDL
4. **Metadata Management**: Track schema relationships, versions, and table mappings
5. **Validation**: Ensure schema compatibility and evolution safety

## Schema Registry Architecture (`backend/schema_registry.py`)

### Core Data Models

```python
@dataclass
class SchemaField:
    """Represents a single field in a schema"""
    name: str
    type: str
    mode: str  # REQUIRED, NULLABLE, REPEATED
    description: Optional[str] = None
    policy_tags: Optional[List[str]] = None
    nested_fields: Optional[List['SchemaField']] = None

@dataclass
class SchemaVersion:
    """Represents a versioned schema"""
    schema_id: str
    version_hash: str
    table_name: str
    database_name: str
    proto_content: Optional[str]
    schema_json: Dict[str, Any]
    fields: List[SchemaField]
    created_at: datetime
    engines_created: List[str]  # Engines where tables exist
```

### Database Schema

The registry uses SQLite for metadata persistence:

```sql
-- Main schemas table
CREATE TABLE IF NOT EXISTS schemas (
    schema_id TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    database_name TEXT NOT NULL DEFAULT 'bigquery_lite',
    current_version_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Schema versions table
CREATE TABLE IF NOT EXISTS schema_versions (
    version_id TEXT PRIMARY KEY,
    schema_id TEXT NOT NULL,
    version_hash TEXT NOT NULL,
    proto_content TEXT,
    schema_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (schema_id) REFERENCES schemas (schema_id)
);

-- Engine table tracking
CREATE TABLE IF NOT EXISTS schema_engine_tables (
    schema_id TEXT,
    engine TEXT,
    table_created BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (schema_id, engine),
    FOREIGN KEY (schema_id) REFERENCES schemas (schema_id)
);
```

## Protobuf to BigQuery Schema Conversion

### Integration with protoc-gen-bq-schema

The registry integrates with the `protoc-gen-bq-schema` tool for schema conversion:

```python
def _generate_bigquery_schema(self, proto_content: str) -> Dict[str, Any]:
    """Generate BigQuery schema using protoc-gen-bq-schema"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write proto file
        proto_file = Path(temp_dir) / "schema.proto"
        proto_file.write_text(proto_content)
        
        # Execute protoc command
        cmd = [
            self.protoc_path,
            f"--proto_path={temp_dir}",
            f"--bq-schema_out={temp_dir}",
            str(proto_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise ProtocExecutionError(f"protoc failed: {result.stderr}")
        
        # Read generated BigQuery schema
        schema_file = temp_dir / "schema.schema"
        return json.loads(schema_file.read_text())
```

### Schema Field Processing

```python
def _parse_schema_fields(self, schema_json: Dict[str, Any]) -> List[SchemaField]:
    """Parse BigQuery schema fields into internal representation"""
    
    fields = []
    for field_data in schema_json:
        field = SchemaField(
            name=field_data['name'],
            type=field_data['type'],
            mode=field_data.get('mode', 'NULLABLE'),
            description=field_data.get('description'),
            policy_tags=field_data.get('policyTags')
        )
        
        # Handle nested fields for RECORD types
        if field.type == 'RECORD' and 'fields' in field_data:
            field.nested_fields = self._parse_schema_fields(field_data['fields'])
        
        fields.append(field)
    
    return fields
```

## Schema Registration Flow

### 1. Schema Upload and Validation

```python
async def register_schema(
    self,
    proto_content: str,
    table_name: str,
    database_name: str = "bigquery_lite",
    description: Optional[str] = None
) -> str:
    """Register a new protobuf schema"""
    
    # Generate schema hash for versioning
    content_hash = hashlib.sha256(proto_content.encode()).hexdigest()[:12]
    schema_id = f"{table_name}_{content_hash}"
    
    # Check for existing schema
    if self._schema_exists(schema_id):
        return schema_id  # Schema already registered
    
    # Generate BigQuery schema
    schema_json = self._generate_bigquery_schema(proto_content)
    fields = self._parse_schema_fields(schema_json)
    
    # Store in database
    self._store_schema(schema_id, table_name, database_name, 
                      proto_content, schema_json, fields, description)
    
    return schema_id
```

### 2. Schema Storage

```python
def _store_schema(self, schema_id: str, table_name: str, 
                 database_name: str, proto_content: str,
                 schema_json: Dict[str, Any], fields: List[SchemaField],
                 description: Optional[str]):
    """Store schema in SQLite database"""
    
    with sqlite3.connect(self.db_path) as conn:
        # Insert main schema record
        conn.execute("""
            INSERT INTO schemas 
            (schema_id, table_name, database_name, current_version_hash, description)
            VALUES (?, ?, ?, ?, ?)
        """, (schema_id, table_name, database_name, schema_id, description))
        
        # Insert schema version
        conn.execute("""
            INSERT INTO schema_versions 
            (version_id, schema_id, version_hash, proto_content, schema_json)
            VALUES (?, ?, ?, ?, ?)
        """, (schema_id, schema_id, schema_id, proto_content, 
              json.dumps(schema_json)))
```

## Schema Translation to SQL DDL

### Integration with Schema Translator

The registry works with `SchemaTranslator` to generate engine-specific DDL:

```python
class SchemaTranslator:
    """Translates BigQuery schemas to engine-specific SQL DDL"""
    
    def translate_to_duckdb_ddl(self, schema_json: Dict[str, Any], 
                               table_name: str, database_name: str) -> str:
        """Generate DuckDB CREATE TABLE statement"""
        
        columns = []
        for field in schema_json:
            column_def = self._translate_field_to_duckdb(field)
            columns.append(column_def)
        
        return f"""
        CREATE TABLE IF NOT EXISTS {database_name}.{table_name} (
            {', '.join(columns)}
        );
        """
    
    def translate_to_clickhouse_ddl(self, schema_json: Dict[str, Any],
                                  table_name: str, database_name: str) -> str:
        """Generate ClickHouse CREATE TABLE statement"""
        
        columns = []
        for field in schema_json:
            column_def = self._translate_field_to_clickhouse(field)
            columns.append(column_def)
        
        return f"""
        CREATE TABLE IF NOT EXISTS {database_name}.{table_name} (
            {', '.join(columns)}
        ) ENGINE = MergeTree()
        ORDER BY tuple();
        """
```

### Type Mapping Logic

```python
def _translate_field_to_duckdb(self, field: Dict[str, Any]) -> str:
    """Translate BigQuery field to DuckDB column definition"""
    
    type_mapping = {
        'STRING': 'VARCHAR',
        'INTEGER': 'BIGINT',
        'FLOAT': 'DOUBLE',
        'BOOLEAN': 'BOOLEAN',
        'TIMESTAMP': 'TIMESTAMP',
        'DATE': 'DATE',
        'TIME': 'TIME',
        'DATETIME': 'TIMESTAMP',
        'RECORD': 'JSON',  # DuckDB JSON type for nested structures
        'REPEATED': 'JSON'  # Arrays stored as JSON
    }
    
    field_name = field['name']
    field_type = type_mapping.get(field['type'], 'VARCHAR')
    is_nullable = field.get('mode', 'NULLABLE') == 'NULLABLE'
    
    column_def = f"{field_name} {field_type}"
    if not is_nullable:
        column_def += " NOT NULL"
    
    return column_def
```

## Schema Evolution and Versioning

### Version Management

```python
def get_schema_versions(self, schema_id: str) -> List[Dict[str, Any]]:
    """Get all versions for a schema"""
    
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.execute("""
            SELECT version_id, version_hash, created_at, 
                   LENGTH(proto_content) as proto_size
            FROM schema_versions 
            WHERE schema_id = ?
            ORDER BY created_at DESC
        """, (schema_id,))
        
        return [dict(row) for row in cursor.fetchall()]
```

### Schema Compatibility Checking

```python
def check_schema_compatibility(self, old_schema: Dict[str, Any], 
                             new_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Check compatibility between schema versions"""
    
    compatibility_issues = []
    
    # Check for removed fields
    old_fields = {f['name'] for f in old_schema}
    new_fields = {f['name'] for f in new_schema}
    
    removed_fields = old_fields - new_fields
    if removed_fields:
        compatibility_issues.append({
            'type': 'FIELD_REMOVAL',
            'fields': list(removed_fields),
            'severity': 'BREAKING'
        })
    
    # Check for type changes
    for field in new_schema:
        field_name = field['name']
        old_field = next((f for f in old_schema if f['name'] == field_name), None)
        
        if old_field and old_field['type'] != field['type']:
            compatibility_issues.append({
                'type': 'TYPE_CHANGE',
                'field': field_name,
                'old_type': old_field['type'],
                'new_type': field['type'],
                'severity': 'BREAKING'
            })
    
    return {
        'is_compatible': len(compatibility_issues) == 0,
        'issues': compatibility_issues
    }
```

## API Integration

### Schema Management Endpoints

The registry provides REST API endpoints through FastAPI integration:

```python
@app.post("/schemas/register", response_model=SchemaRegistrationResponse)
async def register_schema(
    proto_file: UploadFile = File(...),
    table_name: str = Form(...),
    database_name: str = Form("bigquery_lite"),
    description: Optional[str] = Form(None),
    registry: SchemaRegistry = Depends(get_schema_registry)
):
    """Register a new protobuf schema"""
    
    proto_content = await proto_file.read()
    schema_id = await registry.register_schema(
        proto_content.decode(),
        table_name,
        database_name,
        description
    )
    
    schema_version = registry.get_schema_version(schema_id)
    
    return SchemaRegistrationResponse(
        schema_id=schema_id,
        message=f"Schema registered successfully",
        table_name=table_name,
        database_name=database_name,
        field_count=len(schema_version.fields)
    )
```

### Schema Listing and Retrieval

```python
@app.get("/schemas", response_model=List[SchemaMetadata])
async def list_schemas(
    registry: SchemaRegistry = Depends(get_schema_registry)
):
    """List all registered schemas"""
    return registry.list_schemas()

@app.get("/schemas/{schema_id}", response_model=SchemaDetails)
async def get_schema(
    schema_id: str,
    registry: SchemaRegistry = Depends(get_schema_registry)
):
    """Get detailed schema information"""
    return registry.get_schema_details(schema_id)
```

## Error Handling

### Schema Registration Errors

```python
class SchemaRegistryError(Exception):
    """Base exception for schema registry operations"""
    pass

class ProtocExecutionError(SchemaRegistryError):
    """Exception for protoc command execution failures"""
    pass

class SchemaValidationError(SchemaRegistryError):
    """Exception for schema validation failures"""
    pass

# Error handling in endpoints
try:
    schema_id = await registry.register_schema(proto_content, table_name)
except ProtocExecutionError as e:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Protobuf compilation failed: {e}"
    )
except SchemaValidationError as e:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Schema validation failed: {e}"
    )
```

## Performance Considerations

### Schema Caching

```python
class SchemaCache:
    """In-memory cache for frequently accessed schemas"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self._cache = {}
        self._timestamps = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def get_schema(self, schema_id: str) -> Optional[SchemaVersion]:
        """Get schema from cache"""
        if self._is_expired(schema_id):
            self._evict(schema_id)
            return None
        return self._cache.get(schema_id)
    
    def put_schema(self, schema_id: str, schema: SchemaVersion):
        """Store schema in cache"""
        if len(self._cache) >= self.max_size:
            self._evict_lru()
        
        self._cache[schema_id] = schema
        self._timestamps[schema_id] = time.time()
```

### Batch Operations

```python
async def register_schemas_batch(self, schemas: List[Dict[str, Any]]) -> List[str]:
    """Register multiple schemas in a single transaction"""
    
    schema_ids = []
    
    with sqlite3.connect(self.db_path) as conn:
        conn.execute("BEGIN TRANSACTION")
        
        try:
            for schema_data in schemas:
                schema_id = self._register_single_schema(conn, schema_data)
                schema_ids.append(schema_id)
            
            conn.execute("COMMIT")
            
        except Exception as e:
            conn.execute("ROLLBACK")
            raise SchemaRegistryError(f"Batch registration failed: {e}")
    
    return schema_ids
```

## Integration with Protobuf Ingester

The Schema Registry works closely with the Protobuf Ingester for data loading:

```python
# Schema lookup for data ingestion
schema_version = registry.get_schema_version(schema_id)
decoded_messages = ingester.decode_protobuf_messages(
    schema_version.proto_content, 
    pb_data
)

# Convert to database records using schema
prepared_records = ingester.prepare_records_for_insertion(
    decoded_messages, 
    schema_version.schema_json
)
```

This tight integration ensures that data ingestion processes use the exact schema definitions stored in the registry, maintaining data consistency and type safety.

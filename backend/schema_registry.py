#!/usr/bin/env python3
"""
Schema Registry for BigQuery-Lite

Manages protobuf schema registration, versioning, and metadata storage.
Integrates with protoc-gen-bq-schema to convert .proto files to BigQuery schemas,
then stores metadata for table creation across DuckDB and ClickHouse engines.
"""

import os
import json
import hashlib
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    engines_created: List[str]  # List of engines where tables were created


@dataclass
class SchemaMetadata:
    """Schema metadata for API responses"""
    schema_id: str
    table_name: str
    database_name: str
    current_version: str
    total_versions: int
    created_at: datetime
    last_updated: datetime
    engines_available: List[str]
    field_count: int


class SchemaRegistryError(Exception):
    """Custom exception for schema registry operations"""
    pass


class ProtocExecutionError(SchemaRegistryError):
    """Exception for protoc command execution failures"""
    pass


class SchemaRegistry:
    """
    Central registry for managing protobuf schemas and their BigQuery translations.
    
    Responsibilities:
    1. Store and version protobuf schemas
    2. Generate BigQuery schemas using protoc-gen-bq-schema
    3. Track schema metadata and field information
    4. Validate schema compatibility and evolution
    """
    
    def __init__(self, db_path: str = "data/schema_registry.db", protoc_path: str = "protoc"):
        """
        Initialize the Schema Registry
        
        Args:
            db_path: Path to SQLite database file
            protoc_path: Path to protoc binary (default: "protoc" from PATH)
        """
        self.db_path = db_path
        self.protoc_path = protoc_path
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Validate protoc installation
        self._validate_protoc_installation()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Main schemas table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schemas (
                        schema_id TEXT PRIMARY KEY,
                        table_name TEXT NOT NULL,
                        database_name TEXT NOT NULL,
                        current_version_hash TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        last_updated TEXT NOT NULL,
                        total_versions INTEGER DEFAULT 1,
                        UNIQUE(table_name, database_name)
                    )
                ''')
                
                # Schema versions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schema_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schema_id TEXT NOT NULL,
                        version_hash TEXT NOT NULL,
                        proto_content TEXT,
                        schema_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        engines_created TEXT DEFAULT '[]',
                        FOREIGN KEY (schema_id) REFERENCES schemas (schema_id),
                        UNIQUE(schema_id, version_hash)
                    )
                ''')
                
                # Schema fields table for query optimization and metadata
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schema_fields (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schema_id TEXT NOT NULL,
                        version_hash TEXT NOT NULL,
                        field_name TEXT NOT NULL,
                        field_type TEXT NOT NULL,
                        field_mode TEXT NOT NULL,
                        field_path TEXT NOT NULL,  -- dot-separated path for nested fields
                        description TEXT,
                        policy_tags TEXT,  -- JSON array of policy tags
                        is_nested BOOLEAN DEFAULT FALSE,
                        parent_field_id INTEGER,
                        FOREIGN KEY (schema_id) REFERENCES schemas (schema_id),
                        FOREIGN KEY (parent_field_id) REFERENCES schema_fields (id)
                    )
                ''')
                
                # Create indexes for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_schemas_table_name 
                    ON schemas (table_name, database_name)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_schema_versions_hash 
                    ON schema_versions (schema_id, version_hash)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_schema_fields_path 
                    ON schema_fields (schema_id, field_path)
                ''')
                
                conn.commit()
                logger.info(f"Schema registry database initialized at {self.db_path}")
                
        except sqlite3.Error as e:
            raise SchemaRegistryError(f"Failed to initialize database: {e}")
    
    def _validate_protoc_installation(self) -> None:
        """Validate that protoc and protoc-gen-bq-schema are available"""
        try:
            # Check protoc
            result = subprocess.run([self.protoc_path, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise ProtocExecutionError(f"protoc not found or not working: {result.stderr}")
            
            logger.info(f"protoc found: {result.stdout.strip()}")
            
            # Check protoc-gen-bq-schema plugin
            # Note: We'll check this during actual execution since plugin detection is complex
            
        except subprocess.TimeoutExpired:
            raise ProtocExecutionError("protoc command timed out")
        except FileNotFoundError:
            raise ProtocExecutionError(f"protoc binary not found at {self.protoc_path}")
    
    def _generate_schema_hash(self, content: str) -> str:
        """Generate a deterministic hash for schema content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _parse_schema_fields(self, schema_json: List[Dict[str, Any]], parent_path: str = "") -> List[SchemaField]:
        """
        Parse BigQuery schema JSON into SchemaField objects
        
        Args:
            schema_json: List of field definitions from BigQuery schema
            parent_path: Dot-separated path for nested fields
            
        Returns:
            List of SchemaField objects
        """
        fields = []
        
        for field_def in schema_json:
            field_name = field_def.get('name', '')
            field_type = field_def.get('type', '')
            field_mode = field_def.get('mode', 'NULLABLE')
            
            # Build field path
            field_path = f"{parent_path}.{field_name}" if parent_path else field_name
            
            # Extract policy tags if present
            policy_tags = None
            if 'policyTags' in field_def and 'names' in field_def['policyTags']:
                policy_tags = field_def['policyTags']['names']
            
            # Handle nested fields
            nested_fields = None
            if field_type == 'RECORD' and 'fields' in field_def:
                nested_fields = self._parse_schema_fields(field_def['fields'], field_path)
            
            field = SchemaField(
                name=field_name,
                type=field_type,
                mode=field_mode,
                description=field_def.get('description'),
                policy_tags=policy_tags,
                nested_fields=nested_fields
            )
            fields.append(field)
        
        return fields
    
    def _execute_protoc_gen_bq_schema(self, proto_content: str, table_name: str) -> Dict[str, Any]:
        """
        Execute protoc-gen-bq-schema to generate BigQuery schema from protobuf
        
        Args:
            proto_content: Content of the .proto file
            table_name: Target table name for BigQuery
            
        Returns:
            Parsed BigQuery schema JSON
            
        Raises:
            ProtocExecutionError: If protoc execution fails
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Write proto file
            proto_file = temp_dir_path / "schema.proto"
            proto_file.write_text(proto_content)
            
            # Execute protoc with bq-schema plugin
            output_dir = temp_dir_path / "output"
            output_dir.mkdir()
            
            cmd = [
                self.protoc_path,
                f"--proto_path={temp_dir_path}",
                f"--bq-schema_out={output_dir}",
                str(proto_file)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Unknown protoc error"
                    raise ProtocExecutionError(f"protoc-gen-bq-schema failed: {error_msg}")
                
                # Find generated schema file
                schema_files = list(output_dir.glob("*.schema"))
                if not schema_files:
                    raise ProtocExecutionError("No .schema file generated by protoc-gen-bq-schema")
                
                # Read and parse schema JSON
                schema_file = schema_files[0]
                schema_content = schema_file.read_text()
                
                try:
                    return json.loads(schema_content)
                except json.JSONDecodeError as e:
                    raise ProtocExecutionError(f"Invalid JSON in generated schema: {e}")
                    
            except subprocess.TimeoutExpired:
                raise ProtocExecutionError("protoc-gen-bq-schema command timed out")
            except FileNotFoundError:
                raise ProtocExecutionError("protoc-gen-bq-schema plugin not found")
    
    async def register_schema_from_proto(self, 
                                       proto_content: str, 
                                       table_name: str,
                                       database_name: str = "bigquery_lite") -> str:
        """
        Register a schema from protobuf content
        
        Args:
            proto_content: Content of the .proto file
            table_name: Target table name
            database_name: Target database name
            
        Returns:
            Schema ID of the registered schema
            
        Raises:
            SchemaRegistryError: If registration fails
        """
        try:
            # Generate BigQuery schema using protoc-gen-bq-schema
            schema_json = self._execute_protoc_gen_bq_schema(proto_content, table_name)
            
            # Register the schema with both proto and JSON content
            return await self.register_schema_from_json(
                schema_json=schema_json,
                table_name=table_name,
                database_name=database_name,
                proto_content=proto_content
            )
            
        except ProtocExecutionError as e:
            raise SchemaRegistryError(f"Failed to generate schema from proto: {e}")
    
    async def register_schema_from_json(self,
                                      schema_json: Dict[str, Any],
                                      table_name: str,
                                      database_name: str = "bigquery_lite",
                                      proto_content: Optional[str] = None) -> str:
        """
        Register a schema from BigQuery schema JSON
        
        Args:
            schema_json: BigQuery schema JSON (from protoc-gen-bq-schema)
            table_name: Target table name
            database_name: Target database name
            proto_content: Optional original protobuf content
            
        Returns:
            Schema ID of the registered schema
            
        Raises:
            SchemaRegistryError: If registration fails
        """
        try:
            # Validate schema JSON structure
            if not isinstance(schema_json, list) or not schema_json:
                raise SchemaRegistryError("Schema JSON must be a non-empty array of field definitions")
            
            # Generate schema hash
            schema_content = json.dumps(schema_json, sort_keys=True)
            version_hash = self._generate_schema_hash(schema_content)
            
            # Parse schema fields
            fields = self._parse_schema_fields(schema_json)
            
            # Generate schema ID
            schema_id = f"{database_name}.{table_name}"
            
            now = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if schema already exists
                cursor.execute('''
                    SELECT schema_id, current_version_hash FROM schemas 
                    WHERE schema_id = ?
                ''', (schema_id,))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing schema if version is different
                    current_version_hash = existing[1]
                    
                    if current_version_hash == version_hash:
                        logger.info(f"Schema {schema_id} already registered with same version")
                        return schema_id
                    
                    # Add new version
                    cursor.execute('''
                        INSERT INTO schema_versions 
                        (schema_id, version_hash, proto_content, schema_json, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (schema_id, version_hash, proto_content, schema_content, now))
                    
                    # Update main schema record
                    cursor.execute('''
                        UPDATE schemas 
                        SET current_version_hash = ?, last_updated = ?, total_versions = total_versions + 1
                        WHERE schema_id = ?
                    ''', (version_hash, now, schema_id))
                    
                    logger.info(f"Updated schema {schema_id} to new version {version_hash}")
                    
                else:
                    # Create new schema
                    cursor.execute('''
                        INSERT INTO schemas 
                        (schema_id, table_name, database_name, current_version_hash, created_at, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (schema_id, table_name, database_name, version_hash, now, now))
                    
                    # Add version record
                    cursor.execute('''
                        INSERT INTO schema_versions 
                        (schema_id, version_hash, proto_content, schema_json, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (schema_id, version_hash, proto_content, schema_content, now))
                    
                    logger.info(f"Registered new schema {schema_id} with version {version_hash}")
                
                # Store field metadata
                self._store_schema_fields(cursor, schema_id, version_hash, fields)
                
                conn.commit()
                return schema_id
                
        except sqlite3.Error as e:
            raise SchemaRegistryError(f"Database error during schema registration: {e}")
        except Exception as e:
            raise SchemaRegistryError(f"Unexpected error during schema registration: {e}")
    
    def _store_schema_fields(self, 
                           cursor: sqlite3.Cursor, 
                           schema_id: str, 
                           version_hash: str, 
                           fields: List[SchemaField],
                           parent_path: str = "",
                           parent_field_id: Optional[int] = None) -> None:
        """
        Store schema field metadata in database
        
        Args:
            cursor: Database cursor
            schema_id: Schema identifier
            version_hash: Version hash
            fields: List of schema fields
            parent_path: Parent field path for nested fields
            parent_field_id: Parent field database ID for nested fields
        """
        for field in fields:
            field_path = f"{parent_path}.{field.name}" if parent_path else field.name
            
            # Insert field record
            cursor.execute('''
                INSERT INTO schema_fields 
                (schema_id, version_hash, field_name, field_type, field_mode, 
                 field_path, description, policy_tags, is_nested, parent_field_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                schema_id, version_hash, field.name, field.type, field.mode,
                field_path, field.description,
                json.dumps(field.policy_tags) if field.policy_tags else None,
                field.nested_fields is not None, parent_field_id
            ))
            
            # Get the inserted field ID for nested fields
            field_id = cursor.lastrowid
            
            # Recursively store nested fields
            if field.nested_fields:
                self._store_schema_fields(
                    cursor, schema_id, version_hash, field.nested_fields, 
                    field_path, field_id
                )
    
    async def get_schema(self, schema_id: str) -> Optional[SchemaVersion]:
        """
        Get current version of a schema by ID
        
        Args:
            schema_id: Schema identifier
            
        Returns:
            SchemaVersion object or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT s.schema_id, s.table_name, s.database_name, s.current_version_hash,
                           sv.proto_content, sv.schema_json, sv.created_at, sv.engines_created
                    FROM schemas s
                    JOIN schema_versions sv ON s.schema_id = sv.schema_id 
                                           AND s.current_version_hash = sv.version_hash
                    WHERE s.schema_id = ?
                ''', (schema_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                schema_json = json.loads(row[5])
                fields = self._parse_schema_fields(schema_json)
                engines_created = json.loads(row[7])
                
                return SchemaVersion(
                    schema_id=row[0],
                    version_hash=row[3],
                    table_name=row[1],
                    database_name=row[2],
                    proto_content=row[4],
                    schema_json=schema_json,
                    fields=fields,
                    created_at=datetime.fromisoformat(row[6]),
                    engines_created=engines_created
                )
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting schema {schema_id}: {e}")
            return None
    
    async def list_schemas(self) -> List[SchemaMetadata]:
        """
        List all registered schemas with metadata
        
        Returns:
            List of SchemaMetadata objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT s.schema_id, s.table_name, s.database_name, s.current_version_hash,
                           s.total_versions, s.created_at, s.last_updated,
                           COUNT(sf.id) as field_count
                    FROM schemas s
                    LEFT JOIN schema_fields sf ON s.schema_id = sf.schema_id 
                                               AND s.current_version_hash = sf.version_hash
                    GROUP BY s.schema_id, s.table_name, s.database_name, s.current_version_hash,
                             s.total_versions, s.created_at, s.last_updated
                    ORDER BY s.last_updated DESC
                ''')
                
                schemas = []
                for row in cursor.fetchall():
                    schemas.append(SchemaMetadata(
                        schema_id=row[0],
                        table_name=row[1],
                        database_name=row[2],
                        current_version=row[3],
                        total_versions=row[4],
                        created_at=datetime.fromisoformat(row[5]),
                        last_updated=datetime.fromisoformat(row[6]),
                        engines_available=["duckdb", "clickhouse"],  # Default available engines
                        field_count=row[7]
                    ))
                
                return schemas
                
        except sqlite3.Error as e:
            logger.error(f"Database error listing schemas: {e}")
            return []
    
    async def mark_table_created(self, schema_id: str, engine: str) -> None:
        """
        Mark that a table has been created in a specific engine
        
        Args:
            schema_id: Schema identifier
            engine: Engine name (duckdb, clickhouse)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current engines_created list
                cursor.execute('''
                    SELECT sv.engines_created FROM schemas s
                    JOIN schema_versions sv ON s.schema_id = sv.schema_id 
                                           AND s.current_version_hash = sv.version_hash
                    WHERE s.schema_id = ?
                ''', (schema_id,))
                
                row = cursor.fetchone()
                if row:
                    engines_created = json.loads(row[0])
                    if engine not in engines_created:
                        engines_created.append(engine)
                        
                        # Update the engines_created list
                        cursor.execute('''
                            UPDATE schema_versions 
                            SET engines_created = ?
                            WHERE schema_id = ? AND version_hash = (
                                SELECT current_version_hash FROM schemas WHERE schema_id = ?
                            )
                        ''', (json.dumps(engines_created), schema_id, schema_id))
                        
                        conn.commit()
                        logger.info(f"Marked table creation for {schema_id} in {engine}")
                
        except sqlite3.Error as e:
            logger.error(f"Database error marking table created: {e}")
    
    async def delete_schema(self, schema_id: str) -> bool:
        """
        Delete a schema and all its versions
        
        Args:
            schema_id: Schema identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete in correct order due to foreign key constraints
                cursor.execute('DELETE FROM schema_fields WHERE schema_id = ?', (schema_id,))
                cursor.execute('DELETE FROM schema_versions WHERE schema_id = ?', (schema_id,))
                cursor.execute('DELETE FROM schemas WHERE schema_id = ?', (schema_id,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Deleted schema {schema_id}")
                    return True
                else:
                    logger.warning(f"Schema {schema_id} not found for deletion")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"Database error deleting schema {schema_id}: {e}")
            return False
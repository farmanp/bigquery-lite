#!/usr/bin/env python3
"""
BigQuery-Lite Backend API

Enhanced FastAPI backend that provides BigQuery-like functionality using DuckDB and ClickHouse,
with protobuf schema management and automatic table creation capabilities.
This serves as the backend for the React frontend interface.
"""

import asyncio
import uuid
import sqlite3
import json
import tempfile
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, status, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn
import logging

from runners.duckdb_runner import DuckDBRunner
from runners.clickhouse_runner import ClickHouseRunner
from schema_registry import SchemaRegistry, SchemaRegistryError, ProtocExecutionError
from schema_translator import SchemaTranslator, SchemaValidationError
from protobuf_ingester import ProtobufIngester, ProtobufDecodingError, ProtobufIngestionError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database for job history
DB_PATH = "job_history.db"

# =============================================================================
# Pydantic Models
# =============================================================================

# Existing Query Models
class QueryRequest(BaseModel):
    sql: str = Field(..., description="SQL query to execute")
    engine: str = Field(default="duckdb", description="Engine: duckdb or clickhouse")
    priority: int = Field(default=1, ge=1, le=5, description="Query priority")
    estimated_slots: int = Field(default=1, ge=1, le=10, description="Estimated slots")
    max_execution_time: int = Field(default=300, description="Max execution time (seconds)")

class QueryValidationRequest(BaseModel):
    sql: str = Field(..., description="SQL query to validate")
    engine: str = Field(default="duckdb", description="Engine: duckdb or clickhouse")

class QueryValidationResponse(BaseModel):
    valid: bool = Field(..., description="Whether the query is valid")
    estimated_bytes_processed: int = Field(..., description="Estimated bytes to be processed")
    estimated_rows_scanned: int = Field(..., description="Estimated rows to be scanned")
    estimated_execution_time_ms: int = Field(..., description="Estimated execution time in milliseconds")
    affected_tables: List[str] = Field(..., description="List of tables affected by the query")
    query_type: str = Field(..., description="Type of query (SELECT, INSERT, UPDATE, etc.)")
    warnings: List[str] = Field(default_factory=list, description="Query warnings")
    errors: List[str] = Field(default_factory=list, description="Query validation errors")
    suggestion: Optional[str] = Field(None, description="BigQuery-style processing message")

class QueryResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatus(BaseModel):
    job_id: str
    sql: str
    engine: str
    status: str
    priority: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None

class QueryResult(BaseModel):
    job_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_stats: Dict[str, Any] = {}

class SystemStatus(BaseModel):
    total_slots: int
    available_slots: int
    queued_jobs: int
    running_jobs: int
    completed_jobs: int
    engines: Dict[str, str]


# Schema Management Models
class SchemaRegistrationRequest(BaseModel):
    """Request model for schema registration with JSON schema"""
    schema_json: List[Dict[str, Any]] = Field(..., description="BigQuery schema JSON (from protoc-gen-bq-schema)")
    table_name: str = Field(..., description="Target table name", min_length=1, max_length=100)
    database_name: str = Field(default="bigquery_lite", description="Target database name")
    
    @validator('table_name')
    def validate_table_name(cls, v):
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError('Table name must start with letter/underscore and contain only alphanumeric characters and underscores')
        return v


class SchemaRegistrationResponse(BaseModel):
    """Response model for successful schema registration"""
    schema_id: str = Field(..., description="Unique schema identifier")
    version_hash: str = Field(..., description="Version hash of the registered schema")
    table_name: str = Field(..., description="Target table name")
    database_name: str = Field(..., description="Target database name")
    field_count: int = Field(..., description="Number of fields in the schema")
    created_at: datetime = Field(..., description="Registration timestamp")
    message: str = Field(..., description="Success message")


class TableCreationRequest(BaseModel):
    """Request model for table creation from registered schema"""
    engines: List[str] = Field(default=["duckdb"], description="Target engines for table creation")
    if_not_exists: bool = Field(default=True, description="Use IF NOT EXISTS clause")
    create_flattened_view: bool = Field(default=False, description="Also create flattened view for nested schemas")
    
    @validator('engines')
    def validate_engines(cls, v):
        valid_engines = {'duckdb', 'clickhouse'}
        for engine in v:
            if engine not in valid_engines:
                raise ValueError(f'Invalid engine: {engine}. Valid engines: {valid_engines}')
        return v


class TableCreationResponse(BaseModel):
    """Response model for table creation results"""
    schema_id: str = Field(..., description="Schema identifier")
    table_name: str = Field(..., description="Created table name")
    results: Dict[str, Dict[str, Any]] = Field(..., description="Results per engine")
    flattened_view_created: bool = Field(default=False, description="Whether flattened view was created")
    total_engines: int = Field(..., description="Total engines requested")
    successful_engines: int = Field(..., description="Number of engines where table creation succeeded")
    message: str = Field(..., description="Summary message")


class SchemaFieldInfo(BaseModel):
    """Schema field information for API responses"""
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="BigQuery field type")
    mode: str = Field(..., description="Field mode (REQUIRED, NULLABLE, REPEATED)")
    description: Optional[str] = Field(None, description="Field description")
    policy_tags: Optional[List[str]] = Field(None, description="Policy tags for governance")
    nested_fields: Optional[List['SchemaFieldInfo']] = Field(None, description="Nested fields for RECORD types")


# Enable forward references for nested model
SchemaFieldInfo.model_rebuild()


class SchemaInfo(BaseModel):
    """Detailed schema information for API responses"""
    schema_id: str = Field(..., description="Schema identifier")
    table_name: str = Field(..., description="Table name")
    database_name: str = Field(..., description="Database name")
    current_version: str = Field(..., description="Current version hash")
    total_versions: int = Field(..., description="Total number of versions")
    created_at: datetime = Field(..., description="Schema creation timestamp")
    last_updated: datetime = Field(..., description="Last update timestamp")
    field_count: int = Field(..., description="Number of fields")
    fields: List[SchemaFieldInfo] = Field(..., description="Schema field definitions")
    engines_created: List[str] = Field(..., description="Engines where tables have been created")


class SchemaListItem(BaseModel):
    """Schema list item for GET /schemas endpoint"""
    schema_id: str = Field(..., description="Schema identifier")
    table_name: str = Field(..., description="Table name")
    database_name: str = Field(..., description="Database name")
    current_version: str = Field(..., description="Current version hash")
    total_versions: int = Field(..., description="Total number of versions")
    field_count: int = Field(..., description="Number of fields")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_updated: datetime = Field(..., description="Last update timestamp")


class SchemaListResponse(BaseModel):
    """Response model for schema list"""
    schemas: List[SchemaListItem] = Field(..., description="List of registered schemas")
    total: int = Field(..., description="Total number of schemas")


class FlattenedViewResponse(BaseModel):
    """Response model for flattened view SQL"""
    schema_id: str = Field(..., description="Schema identifier")
    table_name: str = Field(..., description="Source table name")
    view_name: str = Field(..., description="Generated view name")
    engine: str = Field(..., description="Target engine")
    sql: str = Field(..., description="CREATE VIEW SQL statement")
    has_nested_fields: bool = Field(..., description="Whether schema has nested fields")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


# Protobuf Data Ingestion Models
class ProtobufIngestionRequest(BaseModel):
    """Request model for protobuf data ingestion"""
    target_engine: str = Field(default="duckdb", description="Target engine for data ingestion")
    batch_size: int = Field(default=1000, ge=1, le=10000, description="Batch size for bulk inserts")
    create_table_if_not_exists: bool = Field(default=True, description="Create table if it doesn't exist")
    
    @validator('target_engine')
    def validate_target_engine(cls, v):
        valid_engines = {'duckdb', 'clickhouse'}
        if v not in valid_engines:
            raise ValueError(f'Invalid engine: {v}. Valid engines: {valid_engines}')
        return v


class ProtobufIngestionResponse(BaseModel):
    """Response model for protobuf data ingestion"""
    schema_id: str = Field(..., description="Schema identifier")
    job_id: str = Field(..., description="Ingestion job identifier")
    status: str = Field(..., description="Ingestion status")
    records_processed: int = Field(..., description="Number of records processed")
    records_inserted: int = Field(..., description="Number of records inserted successfully")
    processing_time: float = Field(..., description="Processing time in seconds")
    errors: List[str] = Field(default_factory=list, description="List of processing errors")
    message: str = Field(..., description="Summary message")

# =============================================================================
# Global State and Dependency Injection
# =============================================================================

# Existing query execution state
runners = {}
job_queue = []
running_jobs = {}
completed_jobs = {}
system_config = {
    "total_slots": 8,
    "available_slots": 8
}

# Schema management state
schema_registry: Optional[SchemaRegistry] = None
schema_translator: Optional[SchemaTranslator] = None
protobuf_ingester: Optional[ProtobufIngester] = None


# Dependency injection functions
async def get_schema_registry() -> SchemaRegistry:
    """Dependency injection for schema registry"""
    global schema_registry
    if schema_registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Schema registry not initialized"
        )
    return schema_registry


async def get_schema_translator() -> SchemaTranslator:
    """Dependency injection for schema translator"""
    global schema_translator
    if schema_translator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Schema translator not initialized"
        )
    return schema_translator


async def get_runners() -> Dict[str, Any]:
    """Dependency injection for database runners"""
    global runners
    if not runners:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database runners not initialized"
        )
    return runners


async def get_protobuf_ingester() -> ProtobufIngester:
    """Dependency injection for protobuf ingester"""
    global protobuf_ingester
    if protobuf_ingester is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protobuf ingester not initialized"
        )
    return protobuf_ingester

def init_database():
    """Initialize SQLite database for job history"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_history (
            job_id TEXT PRIMARY KEY,
            sql TEXT NOT NULL,
            engine TEXT NOT NULL,
            status TEXT NOT NULL,
            priority INTEGER,
            created_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            execution_time REAL,
            error TEXT,
            result_summary TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_job_to_db(job_data):
    """Save job to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO job_history 
        (job_id, sql, engine, status, priority, created_at, started_at, completed_at, execution_time, error, result_summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        job_data['job_id'],
        job_data['sql'],
        job_data['engine'],
        job_data['status'],
        job_data.get('priority'),
        job_data.get('created_at'),
        job_data.get('started_at'),
        job_data.get('completed_at'),
        job_data.get('execution_time'),
        job_data.get('error'),
        json.dumps(job_data.get('result_summary'))
    ))
    
    conn.commit()
    conn.close()

def get_job_history(limit=50):
    """Get job history from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM job_history 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    columns = ['job_id', 'sql', 'engine', 'status', 'priority', 'created_at', 
               'started_at', 'completed_at', 'execution_time', 'error', 'result_summary']
    
    return [dict(zip(columns, row)) for row in rows]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global runners, schema_registry, schema_translator, protobuf_ingester
    
    # Startup
    print("🚀 Starting Enhanced BigQuery-Lite Backend...")
    
    # Initialize database for job history
    init_database()
    
    # Initialize schema management components
    try:
        schema_registry = SchemaRegistry()
        schema_translator = SchemaTranslator()
        protobuf_ingester = ProtobufIngester()
        print("✅ Schema management and protobuf ingestion components initialized")
    except Exception as e:
        print(f"⚠️  Schema management initialization failed: {e}")
        # Continue without schema management if it fails
    
    # Initialize database runners
    runners['duckdb'] = DuckDBRunner()
    runners['clickhouse'] = ClickHouseRunner()
    
    # Initialize DuckDB with sample data
    await runners['duckdb'].initialize()
    
    # Try to connect to ClickHouse
    try:
        await runners['clickhouse'].initialize()
        print("✅ ClickHouse connection established")
    except Exception as e:
        print(f"⚠️  ClickHouse not available: {e}")
    
    # Start background job processor
    asyncio.create_task(process_job_queue())
    
    print("✅ Enhanced backend ready with schema management!")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down backend...")
    for runner in runners.values():
        await runner.cleanup()

# Create FastAPI app
app = FastAPI(
    title="BigQuery-Lite Backend",
    description="Backend API for BigQuery-like local analytics",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def process_job_queue():
    """Background task to process queued jobs"""
    while True:
        if job_queue and system_config["available_slots"] > 0:
            # Get next job
            job = job_queue.pop(0)
            
            # Allocate slot
            system_config["available_slots"] -= 1
            
            # Move to running jobs
            running_jobs[job['job_id']] = job
            job['status'] = 'running'
            job['started_at'] = datetime.now().isoformat()
            
            # Execute job in background
            asyncio.create_task(execute_job(job))
        
        await asyncio.sleep(0.5)

async def execute_job(job):
    """Execute a job"""
    try:
        engine = job['engine']
        runner = runners.get(engine)
        
        if not runner:
            raise Exception(f"Engine {engine} not available")
        
        # Execute query
        result = await runner.execute_query(job['sql'])
        
        # Job completed successfully
        job['status'] = 'completed'
        job['completed_at'] = datetime.now().isoformat()
        job['result'] = result
        
        # Calculate execution time
        start_time = datetime.fromisoformat(job['started_at'])
        end_time = datetime.fromisoformat(job['completed_at'])
        job['execution_time'] = (end_time - start_time).total_seconds()
        
        # Move to completed jobs
        completed_jobs[job['job_id']] = job
        
    except Exception as e:
        # Job failed
        job['status'] = 'failed'
        job['completed_at'] = datetime.now().isoformat()
        job['error'] = str(e)
        
        # Calculate execution time
        if job.get('started_at'):
            start_time = datetime.fromisoformat(job['started_at'])
            end_time = datetime.fromisoformat(job['completed_at'])
            job['execution_time'] = (end_time - start_time).total_seconds()
        
        completed_jobs[job['job_id']] = job
    
    finally:
        # Free up slot
        system_config["available_slots"] += 1
        
        # Remove from running jobs
        if job['job_id'] in running_jobs:
            del running_jobs[job['job_id']]
        
        # Save to database
        save_job_to_db(job)

@app.get("/")
async def root():
    """API status"""
    return {
        "service": "BigQuery-Lite Backend",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "available_engines": list(runners.keys())
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/queries", response_model=QueryResponse)
async def submit_query(query_request: QueryRequest):
    """Submit a query for execution"""
    
    # Validate engine
    if query_request.engine not in runners:
        raise HTTPException(
            status_code=400, 
            detail=f"Engine '{query_request.engine}' not available. Available engines: {list(runners.keys())}"
        )
    
    # Create job
    job_id = str(uuid.uuid4())[:8]
    job = {
        'job_id': job_id,
        'sql': query_request.sql,
        'engine': query_request.engine,
        'priority': query_request.priority,
        'status': 'queued',
        'created_at': datetime.now().isoformat(),
        'estimated_slots': query_request.estimated_slots,
        'max_execution_time': query_request.max_execution_time
    }
    
    # Add to queue (sort by priority)
    job_queue.append(job)
    job_queue.sort(key=lambda x: x['priority'])
    
    return QueryResponse(
        job_id=job_id,
        status="queued",
        message=f"Query submitted with job ID: {job_id}"
    )

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status"""
    
    # Check running jobs
    if job_id in running_jobs:
        job = running_jobs[job_id]
    # Check completed jobs
    elif job_id in completed_jobs:
        job = completed_jobs[job_id]
    # Check queued jobs
    else:
        job = next((j for j in job_queue if j['job_id'] == job_id), None)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return JobStatus(
        job_id=job['job_id'],
        sql=job['sql'],
        engine=job['engine'],
        status=job['status'],
        priority=job['priority'],
        created_at=datetime.fromisoformat(job['created_at']),
        started_at=datetime.fromisoformat(job['started_at']) if job.get('started_at') else None,
        completed_at=datetime.fromisoformat(job['completed_at']) if job.get('completed_at') else None,
        execution_time=job.get('execution_time'),
        error=job.get('error')
    )

@app.get("/jobs/{job_id}/result", response_model=QueryResult)
async def get_job_result(job_id: str):
    """Get job result"""
    
    if job_id not in completed_jobs:
        # Check if job exists but isn't completed
        if (job_id in running_jobs or 
            any(j['job_id'] == job_id for j in job_queue)):
            raise HTTPException(
                status_code=202, 
                detail=f"Job {job_id} is not yet completed"
            )
        else:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = completed_jobs[job_id]
    
    execution_stats = {
        "execution_time": job.get('execution_time'),
        "engine": job['engine'],
        "rows_processed": len(job.get('result', {}).get('data', [])) if job.get('result') else 0
    }
    
    return QueryResult(
        job_id=job['job_id'],
        status=job['status'],
        result=job.get('result'),
        error=job.get('error'),
        execution_stats=execution_stats
    )

@app.get("/jobs")
async def list_jobs(status: Optional[str] = None, limit: int = 50):
    """List jobs"""
    
    jobs = []
    
    # Get from queue
    if status is None or status == "queued":
        jobs.extend([{**j, 'source': 'queue'} for j in job_queue])
    
    # Get from running
    if status is None or status == "running":
        jobs.extend([{**j, 'source': 'running'} for j in running_jobs.values()])
    
    # Get from completed
    if status is None or status in ["completed", "failed"]:
        jobs.extend([{**j, 'source': 'completed'} for j in completed_jobs.values()])
    
    # Sort by creation time and limit
    jobs.sort(key=lambda x: x['created_at'], reverse=True)
    jobs = jobs[:limit]
    
    return {
        "jobs": jobs,
        "total": len(jobs)
    }

@app.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get system status"""
    
    engines_status = {}
    for name, runner in runners.items():
        try:
            engines_status[name] = await runner.get_status()
        except:
            engines_status[name] = "unavailable"
    
    return SystemStatus(
        total_slots=system_config["total_slots"],
        available_slots=system_config["available_slots"],
        queued_jobs=len(job_queue),
        running_jobs=len(running_jobs),
        completed_jobs=len(completed_jobs),
        engines=engines_status
    )

@app.get("/history")
async def get_history(limit: int = 50):
    """Get job history from database"""
    return {
        "history": get_job_history(limit),
        "total": limit
    }

@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a job"""
    
    # Try to remove from queue
    for i, job in enumerate(job_queue):
        if job['job_id'] == job_id:
            job_queue.pop(i)
            return {"message": f"Job {job_id} cancelled"}
    
    # Running jobs can't be easily cancelled in this simple implementation
    if job_id in running_jobs:
        raise HTTPException(status_code=400, detail="Cannot cancel running job")
    
    raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

@app.post("/queries/validate", response_model=QueryValidationResponse)
async def validate_query(validation_request: QueryValidationRequest):
    """Validate a query and estimate data processing without execution"""
    
    # Validate engine
    if validation_request.engine not in runners:
        raise HTTPException(
            status_code=400, 
            detail=f"Engine '{validation_request.engine}' not available. Available engines: {list(runners.keys())}"
        )
    
    try:
        runner = runners[validation_request.engine]
        
        # Check if runner has validate_query method
        if not hasattr(runner, 'validate_query'):
            raise HTTPException(
                status_code=400,
                detail=f"Query validation not supported for engine '{validation_request.engine}'"
            )
        
        # Validate query using the engine's validation method
        validation_result = await runner.validate_query(validation_request.sql)
        
        return QueryValidationResponse(**validation_result)
        
    except Exception as e:
        # Return error as validation failure
        return QueryValidationResponse(
            valid=False,
            estimated_bytes_processed=0,
            estimated_rows_scanned=0,
            estimated_execution_time_ms=0,
            affected_tables=[],
            query_type="UNKNOWN",
            warnings=[],
            errors=[f"Validation failed: {str(e)}"],
            suggestion="Query validation encountered an error. Please check the query syntax."
        )

@app.get("/examples")
async def get_examples():
    """Get example queries"""
    return {
        "examples": [
            {
                "name": "Simple Count",
                "sql": "SELECT COUNT(*) as total_rows FROM nyc_taxi;",
                "engine": "duckdb",
                "description": "Count total rows in the dataset"
            },
            {
                "name": "Payment Analysis",
                "sql": """SELECT 
    payment_type,
    COUNT(*) as trip_count,
    AVG(fare_amount) as avg_fare
FROM nyc_taxi 
WHERE fare_amount > 0 
GROUP BY payment_type 
ORDER BY trip_count DESC;""",
                "engine": "duckdb",
                "description": "Analyze trips by payment type"
            },
            {
                "name": "Hourly Patterns",
                "sql": """SELECT 
    EXTRACT(hour FROM tpep_pickup_datetime) as hour,
    COUNT(*) as trips 
FROM nyc_taxi 
GROUP BY hour 
ORDER BY hour;""",
                "engine": "duckdb",
                "description": "Trip patterns by hour"
            }
        ]
    }


# =============================================================================
# Schema Discovery Endpoints
# =============================================================================

@app.get("/schemas")
async def get_all_schemas(
    engine: str = "duckdb",
    runners: Dict[str, Any] = Depends(get_runners)
):
    """
    Get all datasets and tables from the specified engine
    
    Returns a BigQuery-style schema structure with datasets and their tables.
    This endpoint provides the data needed for the Explorer UI component.
    """
    try:
        # Validate engine
        if engine not in runners:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Engine '{engine}' not available. Available engines: {list(runners.keys())}"
            )
        
        runner = runners[engine]
        
        # Get schema information from the runner
        schema_info = await runner.get_schema_info()
        
        if "error" in schema_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get schema info from {engine}: {schema_info['error']}"
            )
        
        # Transform the schema info into BigQuery-style format
        datasets = {}
        
        # Group tables by dataset (schema)
        tables = schema_info.get("tables", {})
        for table_name, table_info in tables.items():
            # For DuckDB, we'll group by schema or use 'main' as default dataset
            dataset_name = "main"  # Default dataset for DuckDB
            
            if dataset_name not in datasets:
                datasets[dataset_name] = {
                    "dataset_id": dataset_name,
                    "dataset_name": dataset_name,
                    "tables": []
                }
            
            datasets[dataset_name]["tables"].append({
                "table_id": table_name,
                "table_name": table_name,
                "table_type": table_info.get("type", "TABLE"),
                "columns": table_info.get("columns", [])
            })
        
        return {
            "engine": engine,
            "datasets": list(datasets.values()),
            "total_datasets": len(datasets),
            "total_tables": sum(len(ds["tables"]) for ds in datasets.values()),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schemas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error while retrieving schemas: {str(e)}"
        )


@app.get("/schemas/{dataset_id}")
async def get_dataset_tables(
    dataset_id: str,
    engine: str = "duckdb",
    runners: Dict[str, Any] = Depends(get_runners)
):
    """
    Get tables only for a specific dataset
    
    Returns just the tables within a given dataset, useful for when the Explorer
    UI needs to refresh or expand a specific dataset node.
    """
    try:
        # Validate engine
        if engine not in runners:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Engine '{engine}' not available. Available engines: {list(runners.keys())}"
            )
        
        runner = runners[engine]
        
        # Get schema information from the runner
        schema_info = await runner.get_schema_info()
        
        if "error" in schema_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get schema info from {engine}: {schema_info['error']}"
            )
        
        # Filter tables for the requested dataset
        tables = schema_info.get("tables", {})
        dataset_tables = []
        
        # For now, we'll assume all tables belong to 'main' dataset in DuckDB
        # In a real implementation, you might query information_schema.schemata
        if dataset_id == "main":
            for table_name, table_info in tables.items():
                dataset_tables.append({
                    "table_id": table_name,
                    "table_name": table_name,
                    "table_type": table_info.get("type", "TABLE"),
                    "columns": table_info.get("columns", [])
                })
        
        if not dataset_tables and dataset_id != "main":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset '{dataset_id}' not found"
            )
        
        return {
            "engine": engine,
            "dataset_id": dataset_id,
            "dataset_name": dataset_id,
            "tables": dataset_tables,
            "total_tables": len(dataset_tables),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error while retrieving dataset tables: {str(e)}"
        )


# =============================================================================
# Schema Management Endpoints
# =============================================================================

@app.post("/schemas/register", response_model=SchemaRegistrationResponse)
async def register_schema_from_proto_file(
    proto_file: Optional[UploadFile] = File(None),
    schema_file: Optional[UploadFile] = File(None),
    table_name: str = Form(...),
    database_name: str = Form("bigquery_lite"),
    registry: SchemaRegistry = Depends(get_schema_registry)
):
    """
    Register a schema from protobuf file or pre-generated BigQuery schema JSON
    
    Accepts either:
    - proto_file: .proto file (will generate schema using protoc-gen-bq-schema)
    - schema_file: pre-generated .schema JSON file
    
    One of proto_file or schema_file must be provided.
    """
    try:
        # Validate input
        if not proto_file and not schema_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either proto_file or schema_file must be provided"
            )
        
        if proto_file and schema_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either proto_file or schema_file, not both"
            )
        
        # Process protobuf file
        if proto_file:
            if not proto_file.filename.endswith('.proto'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="proto_file must have .proto extension"
                )
            
            # Read protobuf content
            proto_content = await proto_file.read()
            proto_content_str = proto_content.decode('utf-8')
            
            # Register schema from protobuf
            schema_id = await registry.register_schema_from_proto(
                proto_content_str, table_name, database_name
            )
        
        # Process pre-generated schema JSON file
        else:  # schema_file
            if not schema_file.filename.endswith('.schema') and not schema_file.filename.endswith('.json'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="schema_file must have .schema or .json extension"
                )
            
            # Read and parse schema JSON
            schema_content = await schema_file.read()
            try:
                schema_json = json.loads(schema_content.decode('utf-8'))
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid JSON in schema file: {e}"
                )
            
            # Register schema from JSON
            schema_id = await registry.register_schema_from_json(
                schema_json, table_name, database_name
            )
        
        # Get registered schema details
        schema_version = await registry.get_schema(schema_id)
        if not schema_version:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Schema registration succeeded but could not retrieve details"
            )
        
        return SchemaRegistrationResponse(
            schema_id=schema_version.schema_id,
            version_hash=schema_version.version_hash,
            table_name=schema_version.table_name,
            database_name=schema_version.database_name,
            field_count=len(schema_version.fields),
            created_at=schema_version.created_at,
            message=f"Schema registered successfully with {len(schema_version.fields)} fields"
        )
        
    except SchemaRegistryError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Schema registration failed: {e}"
        )
    except ProtocExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"protoc-gen-bq-schema execution failed: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in schema registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during schema registration"
        )


@app.post("/schemas/register-json", response_model=SchemaRegistrationResponse)
async def register_schema_from_json(
    request: SchemaRegistrationRequest,
    registry: SchemaRegistry = Depends(get_schema_registry)
):
    """
    Register a schema from BigQuery schema JSON (alternative to file upload)
    
    Use this endpoint when you have the schema JSON as part of the request body
    rather than as a file upload.
    """
    try:
        # Register schema from JSON
        schema_id = await registry.register_schema_from_json(
            request.schema_json, 
            request.table_name, 
            request.database_name
        )
        
        # Get registered schema details
        schema_version = await registry.get_schema(schema_id)
        if not schema_version:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Schema registration succeeded but could not retrieve details"
            )
        
        return SchemaRegistrationResponse(
            schema_id=schema_version.schema_id,
            version_hash=schema_version.version_hash,
            table_name=schema_version.table_name,
            database_name=schema_version.database_name,
            field_count=len(schema_version.fields),
            created_at=schema_version.created_at,
            message=f"Schema registered successfully with {len(schema_version.fields)} fields"
        )
        
    except SchemaValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Schema validation failed: {e}"
        )
    except SchemaRegistryError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Schema registration failed: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in JSON schema registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during schema registration"
        )


@app.post("/schemas/{schema_id}/tables/create", response_model=TableCreationResponse)
async def create_tables_from_schema(
    schema_id: str,
    request: TableCreationRequest,
    registry: SchemaRegistry = Depends(get_schema_registry),
    translator: SchemaTranslator = Depends(get_schema_translator),
    runners: Dict[str, Any] = Depends(get_runners)
):
    """
    Create tables in specified engines from a registered schema
    
    This endpoint:
    1. Retrieves the schema from the registry
    2. Generates CREATE TABLE SQL for each requested engine
    3. Executes the SQL in each engine
    4. Optionally creates flattened views for nested schemas
    5. Updates the registry with table creation status
    """
    try:
        # Get schema from registry
        schema_version = await registry.get_schema(schema_id)
        if not schema_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema not found: {schema_id}"
            )
        
        results = {}
        successful_engines = 0
        flattened_view_created = False
        
        # Create tables in each requested engine
        for engine in request.engines:
            engine_result = {
                "success": False,
                "sql": None,
                "error": None,
                "execution_time": None
            }
            
            try:
                # Check if engine is available
                if engine not in runners:
                    engine_result["error"] = f"Engine {engine} not available"
                    results[engine] = engine_result
                    continue
                
                # Generate CREATE TABLE SQL
                create_sql = translator.generate_create_table_sql(
                    schema_version.schema_json,
                    schema_version.table_name,
                    engine,
                    schema_version.database_name
                )
                engine_result["sql"] = create_sql
                
                # Execute SQL in the engine
                start_time = datetime.now()
                runner = runners[engine]
                
                # Use the existing query execution method
                if hasattr(runner, 'execute_query'):
                    # Remove IF NOT EXISTS if requested
                    sql_to_execute = create_sql
                    if not request.if_not_exists:
                        sql_to_execute = create_sql.replace("IF NOT EXISTS ", "")
                    
                    execution_result = await runner.execute_query(sql_to_execute)
                    
                    if "error" in execution_result:
                        engine_result["error"] = execution_result["error"]
                    else:
                        engine_result["success"] = True
                        successful_engines += 1
                        
                        # Mark table as created in registry
                        await registry.mark_table_created(schema_id, engine)
                        
                        # Create flattened view if requested and not already created
                        if request.create_flattened_view and not flattened_view_created:
                            try:
                                flattened_sql = translator.generate_flattened_view_sql(
                                    schema_version.schema_json,
                                    schema_version.table_name,
                                    engine,
                                    schema_version.database_name
                                )
                                
                                if flattened_sql:
                                    await runner.execute_query(flattened_sql)
                                    flattened_view_created = True
                                    engine_result["flattened_view_sql"] = flattened_sql
                            except Exception as view_error:
                                logger.warning(f"Failed to create flattened view for {engine}: {view_error}")
                                engine_result["flattened_view_error"] = str(view_error)
                else:
                    engine_result["error"] = f"Engine {engine} does not support query execution"
                
                # Calculate execution time
                execution_time = (datetime.now() - start_time).total_seconds()
                engine_result["execution_time"] = execution_time
                
            except Exception as e:
                logger.error(f"Error creating table in {engine}: {e}")
                engine_result["error"] = str(e)
            
            results[engine] = engine_result
        
        # Generate response message
        if successful_engines == len(request.engines):
            message = f"Successfully created table in all {successful_engines} engines"
        elif successful_engines > 0:
            message = f"Created table in {successful_engines} of {len(request.engines)} engines"
        else:
            message = "Failed to create table in any engine"
        
        if flattened_view_created:
            message += " with flattened view"
        
        return TableCreationResponse(
            schema_id=schema_id,
            table_name=schema_version.table_name,
            results=results,
            flattened_view_created=flattened_view_created,
            total_engines=len(request.engines),
            successful_engines=successful_engines,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in table creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during table creation"
        )


@app.get("/schemas", response_model=SchemaListResponse)
async def list_schemas(
    registry: SchemaRegistry = Depends(get_schema_registry)
):
    """
    List all registered schemas with metadata
    
    Returns a list of all schemas in the registry with basic metadata
    including version information and field counts.
    """
    try:
        # Get all schemas from registry
        schema_metadata_list = await registry.list_schemas()
        
        # Convert to API response format
        schemas = []
        for metadata in schema_metadata_list:
            schemas.append(SchemaListItem(
                schema_id=metadata.schema_id,
                table_name=metadata.table_name,
                database_name=metadata.database_name,
                current_version=metadata.current_version,
                total_versions=metadata.total_versions,
                field_count=metadata.field_count,
                created_at=metadata.created_at,
                last_updated=metadata.last_updated
            ))
        
        return SchemaListResponse(
            schemas=schemas,
            total=len(schemas)
        )
        
    except Exception as e:
        logger.error(f"Error listing schemas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing schemas"
        )


@app.get("/schemas/{schema_id}", response_model=SchemaInfo)
async def get_schema_details(
    schema_id: str,
    registry: SchemaRegistry = Depends(get_schema_registry)
):
    """
    Get detailed information about a specific schema
    
    Returns comprehensive schema information including field definitions,
    version history, and table creation status across engines.
    """
    try:
        # Get schema from registry
        schema_version = await registry.get_schema(schema_id)
        if not schema_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema not found: {schema_id}"
            )
        
        # Convert fields to API format
        def convert_fields(fields) -> List[SchemaFieldInfo]:
            result = []
            for field in fields:
                nested_fields = None
                if field.nested_fields:
                    nested_fields = convert_fields(field.nested_fields)
                
                result.append(SchemaFieldInfo(
                    name=field.name,
                    type=field.type,
                    mode=field.mode,
                    description=field.description,
                    policy_tags=field.policy_tags,
                    nested_fields=nested_fields
                ))
            return result
        
        # Get schema metadata for additional info
        schema_metadata_list = await registry.list_schemas()
        schema_metadata = next(
            (m for m in schema_metadata_list if m.schema_id == schema_id),
            None
        )
        
        if not schema_metadata:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Schema found but metadata not available"
            )
        
        return SchemaInfo(
            schema_id=schema_version.schema_id,
            table_name=schema_version.table_name,
            database_name=schema_version.database_name,
            current_version=schema_version.version_hash,
            total_versions=schema_metadata.total_versions,
            created_at=schema_version.created_at,
            last_updated=schema_metadata.last_updated,
            field_count=len(schema_version.fields),
            fields=convert_fields(schema_version.fields),
            engines_created=schema_version.engines_created
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schema details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving schema"
        )


@app.get("/schemas/{schema_id}/flattened-view", response_model=FlattenedViewResponse)
async def get_flattened_view_sql(
    schema_id: str,
    engine: str = "duckdb",
    registry: SchemaRegistry = Depends(get_schema_registry),
    translator: SchemaTranslator = Depends(get_schema_translator)
):
    """
    Generate flattened view SQL for a schema with nested fields
    
    Returns the CREATE VIEW SQL statement that flattens nested RECORD fields
    for easier analytics. Returns 404 if the schema has no nested fields.
    """
    try:
        # Validate engine
        if engine not in ["duckdb", "clickhouse"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Engine must be 'duckdb' or 'clickhouse'"
            )
        
        # Get schema from registry
        schema_version = await registry.get_schema(schema_id)
        if not schema_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema not found: {schema_id}"
            )
        
        # Check if schema has nested fields
        has_nested = any(field.get('type') == 'RECORD' for field in schema_version.schema_json)
        
        # Generate flattened view SQL
        flattened_sql = translator.generate_flattened_view_sql(
            schema_version.schema_json,
            schema_version.table_name,
            engine,
            schema_version.database_name
        )
        
        if not flattened_sql:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schema has no nested fields - flattened view not applicable"
            )
        
        # Extract view name from SQL
        view_name = f"{schema_version.database_name}.{schema_version.table_name}_flattened"
        
        return FlattenedViewResponse(
            schema_id=schema_id,
            table_name=schema_version.table_name,
            view_name=view_name,
            engine=engine,
            sql=flattened_sql,
            has_nested_fields=has_nested
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating flattened view SQL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while generating flattened view"
        )


@app.delete("/schemas/{schema_id}")
async def delete_schema(
    schema_id: str,
    registry: SchemaRegistry = Depends(get_schema_registry)
):
    """
    Delete a schema and all its versions from the registry
    
    Note: This does not drop the actual tables from the database engines.
    You must manually drop the tables if needed.
    """
    try:
        # Delete schema from registry
        deleted = await registry.delete_schema(schema_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema not found: {schema_id}"
            )
        
        return {
            "message": f"Schema {schema_id} deleted successfully",
            "schema_id": schema_id,
            "note": "Tables in database engines were not dropped automatically"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while deleting schema"
        )


# =============================================================================
# Protobuf Data Ingestion Endpoints
# =============================================================================

@app.post("/schemas/{schema_id}/ingest", response_model=ProtobufIngestionResponse)
async def ingest_protobuf_data(
    schema_id: str,
    pb_file: UploadFile = File(..., description="Binary protobuf file (.pb)"),
    target_engine: str = Form("duckdb"),
    batch_size: int = Form(1000),
    create_table_if_not_exists: bool = Form(True),
    registry: SchemaRegistry = Depends(get_schema_registry),
    translator: SchemaTranslator = Depends(get_schema_translator),
    ingester: ProtobufIngester = Depends(get_protobuf_ingester),
    runners: Dict[str, Any] = Depends(get_runners)
):
    """
    Ingest protobuf-encoded data using a registered schema
    
    This endpoint:
    1. Validates that the schema exists and has a protobuf definition
    2. Decodes the binary protobuf data using the registered schema
    3. Converts decoded messages to database-compatible records
    4. Optionally creates the target table if it doesn't exist
    5. Bulk inserts the records into the specified engine
    
    Args:
        schema_id: ID of the registered schema to use for decoding
        pb_file: Binary protobuf file containing encoded messages (one per line)
        target_engine: Target database engine (duckdb or clickhouse)
        batch_size: Number of records to insert in each batch
        create_table_if_not_exists: Whether to create table if it doesn't exist
    
    Returns:
        ProtobufIngestionResponse with ingestion results and statistics
    """
    start_time = datetime.now()
    job_id = str(uuid.uuid4())[:8]
    
    try:
        # Validate input parameters
        if target_engine not in runners:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Engine '{target_engine}' not available. Available engines: {list(runners.keys())}"
            )
        
        if not pb_file.filename.endswith('.pb'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must have .pb extension"
            )
        
        # Get schema from registry
        schema_version = await registry.get_schema(schema_id)
        if not schema_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema not found: {schema_id}"
            )
        
        # Verify schema has protobuf content
        if not schema_version.proto_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Schema {schema_id} was not registered with a .proto file - protobuf ingestion not supported"
            )
        
        # Read binary protobuf data
        pb_data = await pb_file.read()
        logger.info(f"Read {len(pb_data)} bytes from protobuf file {pb_file.filename}")
        
        # Create table if requested and not exists
        if create_table_if_not_exists:
            try:
                create_sql = translator.generate_create_table_sql(
                    schema_version.schema_json,
                    schema_version.table_name,
                    target_engine,
                    schema_version.database_name
                )
                
                runner = runners[target_engine]
                await runner.execute_query(create_sql)
                logger.info(f"Ensured table exists: {schema_version.database_name}.{schema_version.table_name}")
                
            except Exception as e:
                logger.warning(f"Table creation failed (may already exist): {e}")
        
        # Decode protobuf messages
        try:
            decoded_messages = ingester.decode_protobuf_messages(
                schema_version.proto_content, pb_data
            )
            logger.info(f"Decoded {len(decoded_messages)} protobuf messages")
            
        except ProtobufDecodingError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Protobuf decoding failed: {e}"
            )
        
        # Prepare records for database insertion
        prepared_records = ingester.prepare_records_for_insertion(
            decoded_messages, schema_version.schema_json
        )
        logger.info(f"Prepared {len(prepared_records)} records for insertion")
        
        # Ingest into database
        runner = runners[target_engine]
        records_inserted, errors = await ingester.ingest_to_database(
            prepared_records,
            schema_version.table_name,
            schema_version.database_name,
            runner,
            batch_size
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Determine status
        if records_inserted == len(prepared_records):
            status_str = "completed"
            message = f"Successfully ingested {records_inserted} records into {target_engine}"
        elif records_inserted > 0:
            status_str = "partial"
            message = f"Partially successful: {records_inserted}/{len(prepared_records)} records ingested"
        else:
            status_str = "failed"
            message = "No records were successfully ingested"
        
        if errors:
            message += f" ({len(errors)} batch errors occurred)"
        
        logger.info(f"Ingestion job {job_id} completed: {message}")
        
        return ProtobufIngestionResponse(
            schema_id=schema_id,
            job_id=job_id,
            status=status_str,
            records_processed=len(decoded_messages),
            records_inserted=records_inserted,
            processing_time=processing_time,
            errors=errors,
            message=message
        )
        
    except HTTPException:
        raise
    except ProtobufDecodingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Protobuf decoding failed: {e}"
        )
    except ProtobufIngestionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Protobuf ingestion failed: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in protobuf ingestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during protobuf ingestion"
        )


def main():
    """Run the backend server"""
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
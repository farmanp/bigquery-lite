#!/usr/bin/env python3
"""
BigQuery-Lite Backend API

FastAPI backend that provides BigQuery-like functionality using DuckDB and ClickHouse.
This serves as the backend for the React frontend interface.
"""

import asyncio
import uuid
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from runners.duckdb_runner import DuckDBRunner
from runners.clickhouse_runner import ClickHouseRunner

# Database for job history
DB_PATH = "job_history.db"

# Pydantic models
class QueryRequest(BaseModel):
    sql: str = Field(..., description="SQL query to execute")
    engine: str = Field(default="duckdb", description="Engine: duckdb or clickhouse")
    priority: int = Field(default=1, ge=1, le=5, description="Query priority")
    estimated_slots: int = Field(default=1, ge=1, le=10, description="Estimated slots")
    max_execution_time: int = Field(default=300, description="Max execution time (seconds)")

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

# Global state
runners = {}
job_queue = []
running_jobs = {}
completed_jobs = {}
system_config = {
    "total_slots": 8,
    "available_slots": 8
}

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
    global runners
    
    # Startup
    print("🚀 Starting BigQuery-Lite Backend...")
    
    # Initialize database
    init_database()
    
    # Initialize runners
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
    
    print("✅ Backend ready!")
    
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

def main():
    """Run the backend server"""
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
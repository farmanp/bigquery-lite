#!/usr/bin/env python3
"""
BigQuery-Lite API Server

FastAPI-based REST API for submitting and managing queries
in the BigQuery-like environment using DuckDB and ClickHouse.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import our scheduler
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from scheduler import BigQueryLiteScheduler, QueryJob, QueryStatus, Engine


# Pydantic models for API
class QueryRequest(BaseModel):
    sql: str = Field(..., description="SQL query to execute")
    engine: str = Field(default="duckdb", description="Engine to use (duckdb or clickhouse)")
    priority: int = Field(default=1, ge=1, le=5, description="Query priority (1=highest, 5=lowest)")
    estimated_slots: int = Field(default=1, ge=1, le=10, description="Estimated slots required")
    max_execution_time: int = Field(default=300, ge=1, le=3600, description="Max execution time in seconds")


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
    estimated_slots: int
    actual_slots_used: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    memory_used_mb: float = 0.0
    rows_processed: int = 0
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
    uptime: str


# Global scheduler instance
scheduler: Optional[BigQueryLiteScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global scheduler
    
    # Startup
    scheduler = BigQueryLiteScheduler(total_slots=8)
    
    # Start the scheduler task
    schedule_task = asyncio.create_task(scheduler.schedule_jobs())
    
    # Try to connect to ClickHouse (optional)
    try:
        scheduler.connect_clickhouse()
    except Exception as e:
        print(f"Warning: Could not connect to ClickHouse: {e}")
    
    yield
    
    # Shutdown
    schedule_task.cancel()
    try:
        await schedule_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(
    title="BigQuery-Lite API",
    description="REST API for BigQuery-like analytics using DuckDB and ClickHouse",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", summary="API Status")
async def root():
    """Get API status and basic information"""
    return {
        "service": "BigQuery-Lite API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "submit_query": "/queries",
            "get_job_status": "/jobs/{job_id}",
            "get_job_result": "/jobs/{job_id}/result",
            "list_jobs": "/jobs",
            "system_status": "/status",
            "docs": "/docs"
        }
    }


@app.post("/queries", response_model=QueryResponse, summary="Submit Query")
async def submit_query(query_request: QueryRequest):
    """Submit a SQL query for execution"""
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    try:
        # Validate engine
        engine = Engine.DUCKDB if query_request.engine.lower() == "duckdb" else Engine.CLICKHOUSE
        
        # Submit query to scheduler
        job_id = scheduler.submit_query(
            sql=query_request.sql,
            engine=engine,
            priority=query_request.priority,
            estimated_slots=query_request.estimated_slots
        )
        
        return QueryResponse(
            job_id=job_id,
            status="submitted",
            message=f"Query submitted successfully with job ID: {job_id}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to submit query: {str(e)}")


@app.get("/jobs/{job_id}", response_model=JobStatus, summary="Get Job Status")
async def get_job_status(job_id: str):
    """Get the status of a specific job"""
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    # Check running jobs
    if job_id in scheduler.running_jobs:
        job = scheduler.running_jobs[job_id]
    # Check completed jobs
    elif job_id in scheduler.completed_jobs:
        job = scheduler.completed_jobs[job_id]
    # Check queued jobs
    else:
        queued_job = next((j for j in scheduler.job_queue if j.job_id == job_id), None)
        if queued_job:
            job = queued_job
        else:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Calculate execution time
    execution_time = None
    if job.started_at and job.completed_at:
        execution_time = (job.completed_at - job.started_at).total_seconds()
    elif job.started_at:
        execution_time = (datetime.now() - job.started_at).total_seconds()
    
    return JobStatus(
        job_id=job.job_id,
        sql=job.sql,
        engine=job.engine.value,
        status=job.status.value,
        priority=job.priority,
        estimated_slots=job.estimated_slots,
        actual_slots_used=job.actual_slots_used,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        execution_time=execution_time,
        memory_used_mb=job.memory_used_mb,
        rows_processed=job.rows_processed,
        error=job.error
    )


@app.get("/jobs/{job_id}/result", response_model=QueryResult, summary="Get Query Result")
async def get_job_result(job_id: str):
    """Get the result of a completed job"""
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    # Only completed jobs have results
    if job_id not in scheduler.completed_jobs:
        # Check if job exists but isn't completed
        if (job_id in scheduler.running_jobs or 
            any(j.job_id == job_id for j in scheduler.job_queue)):
            raise HTTPException(
                status_code=202, 
                detail=f"Job {job_id} is not yet completed"
            )
        else:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = scheduler.completed_jobs[job_id]
    
    # Prepare execution stats
    execution_stats = {
        "execution_time": (job.completed_at - job.started_at).total_seconds() if job.started_at and job.completed_at else None,
        "memory_used_mb": job.memory_used_mb,
        "rows_processed": job.rows_processed,
        "slots_used": job.actual_slots_used,
        "engine": job.engine.value
    }
    
    return QueryResult(
        job_id=job.job_id,
        status=job.status.value,
        result=job.result,
        error=job.error,
        execution_stats=execution_stats
    )


@app.get("/jobs", summary="List All Jobs")
async def list_jobs(status: Optional[str] = None, limit: int = 50):
    """List jobs with optional status filtering"""
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    jobs = []
    
    # Collect jobs from different sources
    if status is None or status.lower() == "queued":
        jobs.extend(scheduler.job_queue)
    
    if status is None or status.lower() == "running":
        jobs.extend(scheduler.running_jobs.values())
    
    if status is None or status.lower() in ["completed", "failed"]:
        jobs.extend(scheduler.completed_jobs.values())
    
    # Sort by creation time (newest first) and limit
    jobs.sort(key=lambda x: x.created_at, reverse=True)
    jobs = jobs[:limit]
    
    # Convert to response format
    job_list = []
    for job in jobs:
        execution_time = None
        if job.started_at and job.completed_at:
            execution_time = (job.completed_at - job.started_at).total_seconds()
        elif job.started_at:
            execution_time = (datetime.now() - job.started_at).total_seconds()
        
        job_list.append({
            "job_id": job.job_id,
            "status": job.status.value,
            "engine": job.engine.value,
            "priority": job.priority,
            "created_at": job.created_at.isoformat(),
            "execution_time": execution_time,
            "sql_preview": job.sql[:100] + "..." if len(job.sql) > 100 else job.sql
        })
    
    return {
        "jobs": job_list,
        "total": len(job_list),
        "filtered_by_status": status
    }


@app.get("/status", response_model=SystemStatus, summary="System Status")
async def get_system_status():
    """Get overall system status and metrics"""
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    # Calculate metrics
    available_slots = sum(1 for slot in scheduler.slots.values() if slot.is_available)
    queued_jobs = len(scheduler.job_queue)
    running_jobs = len(scheduler.running_jobs)
    completed_jobs = len(scheduler.completed_jobs)
    
    return SystemStatus(
        total_slots=scheduler.total_slots,
        available_slots=available_slots,
        queued_jobs=queued_jobs,
        running_jobs=running_jobs,
        completed_jobs=completed_jobs,
        uptime="Running"  # Simple uptime indicator
    )


@app.delete("/jobs/{job_id}", summary="Cancel Job")
async def cancel_job(job_id: str):
    """Cancel a queued or running job"""
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    # Try to find and remove from queue
    for i, job in enumerate(scheduler.job_queue):
        if job.job_id == job_id:
            job.status = QueryStatus.CANCELLED
            scheduler.job_queue.pop(i)
            return {"message": f"Job {job_id} cancelled successfully"}
    
    # Check if it's running (harder to cancel, but we can mark it)
    if job_id in scheduler.running_jobs:
        scheduler.running_jobs[job_id].status = QueryStatus.CANCELLED
        return {"message": f"Job {job_id} marked for cancellation"}
    
    raise HTTPException(status_code=404, detail=f"Job {job_id} not found or already completed")


@app.post("/queries/batch", summary="Submit Batch Queries")
async def submit_batch_queries(queries: List[QueryRequest]):
    """Submit multiple queries as a batch"""
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    if len(queries) > 20:  # Limit batch size
        raise HTTPException(status_code=400, detail="Batch size limited to 20 queries")
    
    job_ids = []
    
    for query_request in queries:
        try:
            engine = Engine.DUCKDB if query_request.engine.lower() == "duckdb" else Engine.CLICKHOUSE
            
            job_id = scheduler.submit_query(
                sql=query_request.sql,
                engine=engine,
                priority=query_request.priority,
                estimated_slots=query_request.estimated_slots
            )
            
            job_ids.append({
                "job_id": job_id,
                "status": "submitted",
                "sql_preview": query_request.sql[:50] + "..." if len(query_request.sql) > 50 else query_request.sql
            })
            
        except Exception as e:
            job_ids.append({
                "job_id": None,
                "status": "failed",
                "error": str(e),
                "sql_preview": query_request.sql[:50] + "..." if len(query_request.sql) > 50 else query_request.sql
            })
    
    return {
        "batch_id": str(uuid.uuid4())[:8],
        "submitted_jobs": len([j for j in job_ids if j["job_id"]]),
        "failed_jobs": len([j for j in job_ids if not j["job_id"]]),
        "jobs": job_ids
    }


# Example queries endpoint for testing
@app.get("/examples", summary="Example Queries")
async def get_example_queries():
    """Get example queries for testing the API"""
    return {
        "examples": [
            {
                "name": "Simple Count",
                "sql": "SELECT COUNT(*) FROM nyc_taxi",
                "engine": "duckdb",
                "description": "Count total rows in the dataset"
            },
            {
                "name": "Payment Type Analysis",
                "sql": "SELECT payment_type, COUNT(*) as trips, AVG(fare_amount) as avg_fare FROM nyc_taxi WHERE fare_amount > 0 GROUP BY payment_type ORDER BY trips DESC",
                "engine": "duckdb",
                "description": "Analyze trips by payment type"
            },
            {
                "name": "Hourly Trip Patterns",
                "sql": "SELECT EXTRACT(hour FROM tpep_pickup_datetime) as hour, COUNT(*) as trips FROM nyc_taxi GROUP BY hour ORDER BY hour",
                "engine": "duckdb",
                "description": "Trip patterns by hour of day"
            },
            {
                "name": "Top Expensive Trips",
                "sql": "SELECT * FROM nyc_taxi WHERE fare_amount > 0 ORDER BY total_amount DESC LIMIT 10",
                "engine": "duckdb",
                "description": "Find the most expensive trips"
            }
        ]
    }


def main():
    """Run the API server"""
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
BigQuery-Like Slot Scheduler Simulation

This script simulates BigQuery's slot-based resource allocation and query scheduling.
It manages query queues, resource allocation, and execution monitoring.
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import random

import duckdb
import clickhouse_connect
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich import box

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console()


class QueryStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Engine(Enum):
    DUCKDB = "duckdb"
    CLICKHOUSE = "clickhouse"


@dataclass
class QueryJob:
    """Represents a query job in the scheduler"""
    job_id: str
    sql: str
    engine: Engine
    priority: int = 1  # 1=highest, 5=lowest
    estimated_slots: int = 1
    max_execution_time: int = 300  # seconds
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: QueryStatus = QueryStatus.QUEUED
    result: Optional[Any] = None
    error: Optional[str] = None
    actual_slots_used: int = 0
    memory_used_mb: float = 0.0
    rows_processed: int = 0


@dataclass
class Slot:
    """Represents a compute slot"""
    slot_id: str
    is_available: bool = True
    current_job: Optional[str] = None
    allocated_at: Optional[datetime] = None
    memory_limit_mb: int = 1024
    cpu_cores: float = 1.0


class BigQueryLiteScheduler:
    """Simulates BigQuery's slot-based scheduling system"""
    
    def __init__(self, total_slots: int = 10, duckdb_path: str = ":memory:"):
        self.total_slots = total_slots
        self.slots: Dict[str, Slot] = {}
        self.job_queue: List[QueryJob] = []
        self.running_jobs: Dict[str, QueryJob] = {}
        self.completed_jobs: Dict[str, QueryJob] = {}
        self.executor = ThreadPoolExecutor(max_workers=total_slots)
        
        # Initialize slots
        for i in range(total_slots):
            slot_id = f"slot_{i:03d}"
            self.slots[slot_id] = Slot(
                slot_id=slot_id,
                memory_limit_mb=random.randint(512, 2048),
                cpu_cores=random.uniform(0.5, 2.0)
            )
        
        # Initialize database connections
        self.duckdb_conn = duckdb.connect(duckdb_path)
        self.clickhouse_conn = None
        
        # Setup sample data in DuckDB
        self._setup_sample_data()
        
        console.print(f"[green]✓[/green] Scheduler initialized with {total_slots} slots")
    
    def _setup_sample_data(self):
        """Setup sample data for testing"""
        try:
            # Load NYC taxi data if available
            self.duckdb_conn.execute("""
                CREATE VIEW IF NOT EXISTS nyc_taxi AS 
                SELECT * FROM read_parquet('../data/nyc_taxi.parquet')
            """)
            console.print("[green]✓[/green] NYC taxi data loaded into DuckDB")
        except Exception as e:
            # Create sample data if parquet file not available
            logger.warning(f"Could not load parquet file: {e}")
            self.duckdb_conn.execute("""
                CREATE TABLE sample_data AS 
                SELECT 
                    row_number() OVER () as id,
                    random() * 100 as value,
                    'category_' || (random() * 5)::int as category,
                    NOW() - INTERVAL (random() * 30) DAY as created_at
                FROM range(10000)
            """)
            console.print("[yellow]⚠[/yellow] Created sample data in DuckDB")
    
    def connect_clickhouse(self, host: str = "localhost", port: int = 8123, 
                          username: str = "admin", password: str = "password"):
        """Connect to ClickHouse cluster"""
        try:
            self.clickhouse_conn = clickhouse_connect.get_client(
                host=host, port=port, username=username, password=password
            )
            console.print("[green]✓[/green] Connected to ClickHouse")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            console.print("[red]✗[/red] ClickHouse connection failed")
    
    def submit_query(self, sql: str, engine: Engine = Engine.DUCKDB, 
                    priority: int = 1, estimated_slots: int = 1) -> str:
        """Submit a query to the scheduler"""
        job_id = str(uuid.uuid4())[:8]
        
        job = QueryJob(
            job_id=job_id,
            sql=sql,
            engine=engine,
            priority=priority,
            estimated_slots=estimated_slots
        )
        
        self.job_queue.append(job)
        self.job_queue.sort(key=lambda x: (x.priority, x.created_at))
        
        console.print(f"[blue]📝[/blue] Query {job_id} submitted to queue")
        return job_id
    
    def get_available_slots(self, required_slots: int = 1) -> List[str]:
        """Get available slots for a job"""
        available = [
            slot_id for slot_id, slot in self.slots.items() 
            if slot.is_available
        ]
        return available[:required_slots]
    
    async def execute_query(self, job: QueryJob) -> QueryJob:
        """Execute a query job"""
        job.started_at = datetime.now()
        job.status = QueryStatus.RUNNING
        
        try:
            if job.engine == Engine.DUCKDB:
                result = await self._execute_duckdb_query(job)
            elif job.engine == Engine.CLICKHOUSE:
                result = await self._execute_clickhouse_query(job)
            else:
                raise ValueError(f"Unsupported engine: {job.engine}")
            
            job.result = result
            job.status = QueryStatus.COMPLETED
            job.completed_at = datetime.now()
            
        except Exception as e:
            job.error = str(e)
            job.status = QueryStatus.FAILED
            job.completed_at = datetime.now()
            logger.error(f"Query {job.job_id} failed: {e}")
        
        return job
    
    async def _execute_duckdb_query(self, job: QueryJob) -> Dict:
        """Execute query in DuckDB"""
        # Simulate resource usage
        start_time = time.time()
        
        try:
            # Enable profiling for this query
            self.duckdb_conn.execute("PRAGMA enable_profiling")
            
            # Execute the query
            result = self.duckdb_conn.execute(job.sql).fetchdf()
            
            execution_time = time.time() - start_time
            
            # Simulate resource metrics
            job.memory_used_mb = random.uniform(100, 1000)
            job.rows_processed = len(result) if hasattr(result, '__len__') else 0
            
            return {
                "rows": len(result) if hasattr(result, '__len__') else 1,
                "execution_time": execution_time,
                "engine": "duckdb",
                "data": result.to_dict('records') if hasattr(result, 'to_dict') else str(result)
            }
            
        except Exception as e:
            raise Exception(f"DuckDB execution failed: {e}")
    
    async def _execute_clickhouse_query(self, job: QueryJob) -> Dict:
        """Execute query in ClickHouse"""
        if not self.clickhouse_conn:
            raise Exception("ClickHouse not connected")
        
        start_time = time.time()
        
        try:
            result = self.clickhouse_conn.query(job.sql)
            execution_time = time.time() - start_time
            
            # Simulate resource metrics
            job.memory_used_mb = random.uniform(200, 2000)
            job.rows_processed = result.row_count if hasattr(result, 'row_count') else 0
            
            return {
                "rows": result.row_count if hasattr(result, 'row_count') else 0,
                "execution_time": execution_time,
                "engine": "clickhouse",
                "data": result.result_rows if hasattr(result, 'result_rows') else []
            }
            
        except Exception as e:
            raise Exception(f"ClickHouse execution failed: {e}")
    
    async def schedule_jobs(self):
        """Main scheduling loop"""
        while True:
            if not self.job_queue:
                await asyncio.sleep(1)
                continue
            
            # Get next job
            job = self.job_queue[0]
            
            # Check if we have available slots
            available_slots = self.get_available_slots(job.estimated_slots)
            
            if len(available_slots) >= job.estimated_slots:
                # Remove from queue and start execution
                self.job_queue.pop(0)
                
                # Allocate slots
                allocated_slots = available_slots[:job.estimated_slots]
                for slot_id in allocated_slots:
                    self.slots[slot_id].is_available = False
                    self.slots[slot_id].current_job = job.job_id
                    self.slots[slot_id].allocated_at = datetime.now()
                
                job.actual_slots_used = len(allocated_slots)
                self.running_jobs[job.job_id] = job
                
                # Execute job asynchronously
                asyncio.create_task(self._execute_and_cleanup(job, allocated_slots))
                
                console.print(f"[green]🚀[/green] Started job {job.job_id} on {len(allocated_slots)} slots")
            
            await asyncio.sleep(0.5)
    
    async def _execute_and_cleanup(self, job: QueryJob, allocated_slots: List[str]):
        """Execute job and cleanup resources"""
        try:
            # Execute the job
            completed_job = await self.execute_query(job)
            
            # Move to completed jobs
            if job.job_id in self.running_jobs:
                del self.running_jobs[job.job_id]
            self.completed_jobs[job.job_id] = completed_job
            
            # Free up slots
            for slot_id in allocated_slots:
                self.slots[slot_id].is_available = True
                self.slots[slot_id].current_job = None
                self.slots[slot_id].allocated_at = None
            
            execution_time = (completed_job.completed_at - completed_job.started_at).total_seconds()
            status_color = "green" if completed_job.status == QueryStatus.COMPLETED else "red"
            
            console.print(f"[{status_color}]✓[/{status_color}] Job {job.job_id} {completed_job.status.value} in {execution_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error in job execution: {e}")
    
    def get_status_table(self) -> Table:
        """Generate a status table for display"""
        table = Table(title="BigQuery-Lite Scheduler Status", box=box.ROUNDED)
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        # Calculate metrics
        available_slots = sum(1 for slot in self.slots.values() if slot.is_available)
        queue_size = len(self.job_queue)
        running_jobs = len(self.running_jobs)
        completed_jobs = len(self.completed_jobs)
        
        table.add_row("Available Slots", f"{available_slots}/{self.total_slots}")
        table.add_row("Queued Jobs", str(queue_size))
        table.add_row("Running Jobs", str(running_jobs))
        table.add_row("Completed Jobs", str(completed_jobs))
        
        return table
    
    def get_jobs_table(self) -> Table:
        """Generate a jobs status table"""
        table = Table(title="Job Status", box=box.ROUNDED)
        
        table.add_column("Job ID", style="cyan")
        table.add_column("Engine", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Slots", style="green")
        table.add_column("Duration", style="magenta")
        table.add_column("Memory (MB)", style="red")
        
        # Add running jobs
        for job in self.running_jobs.values():
            duration = (datetime.now() - job.started_at).total_seconds() if job.started_at else 0
            table.add_row(
                job.job_id,
                job.engine.value,
                job.status.value,
                str(job.actual_slots_used),
                f"{duration:.1f}s",
                f"{job.memory_used_mb:.1f}"
            )
        
        # Add last 5 completed jobs
        recent_completed = list(self.completed_jobs.values())[-5:]
        for job in recent_completed:
            duration = (job.completed_at - job.started_at).total_seconds() if job.started_at and job.completed_at else 0
            status_color = "green" if job.status == QueryStatus.COMPLETED else "red"
            table.add_row(
                job.job_id,
                job.engine.value,
                f"[{status_color}]{job.status.value}[/{status_color}]",
                str(job.actual_slots_used),
                f"{duration:.1f}s",
                f"{job.memory_used_mb:.1f}"
            )
        
        return table
    
    async def monitor_dashboard(self):
        """Display a live monitoring dashboard"""
        with Live(console=console, refresh_per_second=2) as live:
            while True:
                # Create panels
                status_panel = Panel(self.get_status_table(), title="System Status")
                jobs_panel = Panel(self.get_jobs_table(), title="Recent Jobs")
                
                # Combine panels
                from rich.columns import Columns
                display = Columns([status_panel, jobs_panel])
                
                live.update(display)
                await asyncio.sleep(1)


async def demo_scheduler():
    """Demo the scheduler with sample queries"""
    scheduler = BigQueryLiteScheduler(total_slots=6)
    
    # Start the scheduler
    schedule_task = asyncio.create_task(scheduler.schedule_jobs())
    
    # Wait a moment for scheduler to start
    await asyncio.sleep(1)
    
    # Submit demo queries
    demo_queries = [
        ("SELECT COUNT(*) FROM nyc_taxi", Engine.DUCKDB, 1, 1),
        ("SELECT payment_type, COUNT(*) FROM nyc_taxi GROUP BY payment_type", Engine.DUCKDB, 2, 2),
        ("SELECT AVG(fare_amount) FROM nyc_taxi WHERE fare_amount > 0", Engine.DUCKDB, 1, 1),
        ("SELECT * FROM nyc_taxi ORDER BY fare_amount DESC LIMIT 10", Engine.DUCKDB, 3, 1),
        ("SELECT DATE(tpep_pickup_datetime) as date, COUNT(*) FROM nyc_taxi GROUP BY date ORDER BY date", Engine.DUCKDB, 2, 2),
    ]
    
    console.print("[blue]🚀 Submitting demo queries...[/blue]")
    
    for sql, engine, priority, slots in demo_queries:
        job_id = scheduler.submit_query(sql, engine, priority, slots)
        await asyncio.sleep(random.uniform(0.5, 2.0))  # Stagger submissions
    
    # Monitor for 30 seconds
    monitor_task = asyncio.create_task(scheduler.monitor_dashboard())
    
    try:
        await asyncio.wait_for(monitor_task, timeout=30.0)
    except asyncio.TimeoutError:
        console.print("[yellow]Demo completed![/yellow]")
    
    # Cancel tasks
    schedule_task.cancel()
    monitor_task.cancel()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BigQuery-Lite Slot Scheduler")
    parser.add_argument("--slots", type=int, default=6, help="Number of compute slots")
    parser.add_argument("--demo", action="store_true", help="Run demo mode")
    parser.add_argument("--clickhouse-host", default="localhost", help="ClickHouse host")
    parser.add_argument("--clickhouse-port", type=int, default=8123, help="ClickHouse port")
    
    args = parser.parse_args()
    
    if args.demo:
        console.print("[bold blue]Starting BigQuery-Lite Scheduler Demo[/bold blue]")
        asyncio.run(demo_scheduler())
    else:
        console.print("[bold blue]BigQuery-Lite Scheduler[/bold blue]")
        console.print("Use --demo to run demonstration mode")


if __name__ == "__main__":
    main()
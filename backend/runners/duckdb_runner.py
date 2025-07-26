#!/usr/bin/env python3
"""
DuckDB Runner

Handles query execution using DuckDB for embedded analytics.
Provides BigQuery-like functionality with query plans and performance metrics.
"""

import duckdb
import time
import os
import asyncio
from typing import Dict, Any, Optional
import pandas as pd


class DuckDBRunner:
    """DuckDB query execution engine"""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.connection = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize DuckDB connection and load sample data"""
        try:
            # Create connection
            self.connection = duckdb.connect(self.db_path)
            
            # Enable profiling for query plans
            self.connection.execute("PRAGMA enable_profiling")
            self.connection.execute("PRAGMA profiling_mode = 'detailed'")
            
            # Set memory limit
            self.connection.execute("PRAGMA memory_limit='2GB'")
            
            # Create bigquery_lite schema if it doesn't exist
            self.connection.execute("CREATE SCHEMA IF NOT EXISTS bigquery_lite")
            
            # Load NYC taxi data if available
            data_path = "../data/nyc_taxi.parquet"
            if os.path.exists(data_path):
                self.connection.execute(f"""
                    CREATE VIEW IF NOT EXISTS nyc_taxi AS 
                    SELECT * FROM read_parquet('{data_path}')
                """)
                print("✅ NYC taxi data loaded into DuckDB")
            else:
                # Create sample data if parquet file not available
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS nyc_taxi AS 
                    SELECT 
                        row_number() OVER () as id,
                        'cash'::VARCHAR as payment_type,
                        random() * 50 + 5 as fare_amount,
                        random() * 10 + 1 as trip_distance,
                        random() * 60 + 10 as total_amount,
                        random() * 5 + 1 as passenger_count,
                        (NOW() - INTERVAL (random() * 30) DAY)::TIMESTAMP as tpep_pickup_datetime,
                        (NOW() - INTERVAL (random() * 30) DAY + INTERVAL (random() * 120) MINUTE)::TIMESTAMP as tpep_dropoff_datetime,
                        random() * 10 as tip_amount
                    FROM range(50000)
                """)
                print("⚠️  Created sample NYC taxi data in DuckDB")
            
            # Create additional sample tables for testing
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS sample_data AS 
                SELECT 
                    row_number() OVER () as id,
                    random() * 1000 as value,
                    'category_' || (random() * 5)::int as category,
                    NOW() - INTERVAL (random() * 365) DAY as created_at
                FROM range(10000)
            """)
            
            # Register custom UDFs
            self._register_udfs()
            
            self.is_initialized = True
            print("✅ DuckDB runner initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize DuckDB: {e}")
            raise e
    
    def _register_udfs(self):
        """Register custom User Defined Functions"""
        print("⚠️  UDF registration temporarily disabled for compatibility")
        pass
    
    async def execute_query(self, sql: str) -> Dict[str, Any]:
        """Execute a SQL query and return results with performance metrics"""
        
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Clear previous profiling data
            self.connection.execute("PRAGMA profiling_output = '/dev/null'")
            
            # Execute the query
            result = self.connection.execute(sql).fetchdf()
            
            execution_time = time.time() - start_time
            
            # Get query plan (simplified version)
            try:
                plan_result = self.connection.execute(f"EXPLAIN ANALYZE {sql}").fetchall()
                query_plan = "\n".join([str(row[0]) for row in plan_result])
            except:
                query_plan = "Query plan not available"
            
            # Convert DataFrame to list of dictionaries for JSON serialization
            if isinstance(result, pd.DataFrame):
                data = result.to_dict('records')
                
                # Handle NaN values and non-serializable types
                for row in data:
                    for key, value in row.items():
                        if pd.isna(value):
                            row[key] = None
                        elif hasattr(value, 'item'):  # numpy types
                            row[key] = value.item()
                        elif hasattr(value, 'isoformat'):  # datetime types
                            row[key] = value.isoformat()
            else:
                # Handle scalar results
                data = [{"result": result}] if result is not None else []
            
            # Simulate some additional metrics (in a real implementation, 
            # these would come from DuckDB's actual profiling)
            row_count = len(data)
            estimated_memory = max(0.1, row_count * 0.001)  # Rough estimate
            
            return {
                "data": data,
                "execution_time": execution_time,
                "rows": row_count,
                "engine": "duckdb",
                "query_plan": query_plan,
                "performance_metrics": {
                    "execution_time": execution_time,
                    "memory_used_mb": estimated_memory,
                    "rows_processed": row_count,
                    "engine": "duckdb",
                    "cpu_time": execution_time * 0.8,  # Simulated
                    "io_wait": execution_time * 0.1,   # Simulated
                    "network_time": 0.0                # Local execution
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Return error information
            return {
                "data": [],
                "execution_time": execution_time,
                "rows": 0,
                "engine": "duckdb",
                "error": str(e),
                "query_plan": f"Error executing query: {str(e)}"
            }
    
    async def get_status(self) -> str:
        """Get runner status"""
        if not self.is_initialized:
            return "not_initialized"
        
        try:
            # Test connection with a simple query
            self.connection.execute("SELECT 1").fetchone()
            return "available"
        except:
            return "error"
    
    async def get_schema_info(self) -> Dict[str, Any]:
        """Get information about available tables and schemas"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Get table information
            tables_result = self.connection.execute("""
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = 'main'
            """).fetchall()
            
            tables = {}
            for table_name, table_type in tables_result:
                # Get column information for each table
                columns_result = self.connection.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND table_schema = 'main'
                """).fetchall()
                
                tables[table_name] = {
                    "type": table_type,
                    "columns": [{"name": col[0], "type": col[1]} for col in columns_result]
                }
            
            return {
                "engine": "duckdb",
                "database": self.db_path,
                "tables": tables
            }
            
        except Exception as e:
            return {
                "engine": "duckdb",
                "error": str(e)
            }
    
    async def cleanup(self):
        """Clean up resources"""
        if self.connection:
            self.connection.close()
            self.connection = None
        self.is_initialized = False
        print("🧹 DuckDB runner cleaned up")
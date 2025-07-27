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
import re
from typing import Dict, Any, Optional, List, Tuple
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
    
    async def validate_query(self, sql: str) -> Dict[str, Any]:
        """Validate query and estimate data processing without execution"""
        
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        warnings = []
        errors = []
        
        try:
            # Clean up SQL for analysis
            clean_sql = sql.strip()
            if not clean_sql:
                return {
                    "valid": False,
                    "estimated_bytes_processed": 0,
                    "estimated_rows_scanned": 0,
                    "estimated_execution_time_ms": 0,
                    "affected_tables": [],
                    "query_type": "UNKNOWN",
                    "warnings": warnings,
                    "errors": ["Empty query"],
                    "suggestion": "Please enter a SQL query."
                }
            
            # Determine query type
            query_type = self._get_query_type(clean_sql)
            
            # Extract table names from query
            affected_tables = self._extract_table_names(clean_sql)
            
            # Use EXPLAIN to validate and get query plan without execution
            try:
                explain_result = self.connection.execute(f"EXPLAIN {clean_sql}").fetchall()
                valid = True
            except Exception as e:
                errors.append(str(e))
                valid = False
                explain_result = []
            
            # Estimate data size for each table
            estimated_bytes = 0
            estimated_rows = 0
            
            if valid and affected_tables:
                for table in affected_tables:
                    try:
                        # Get table statistics - use row count and estimate bytes
                        row_count_result = self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                        table_rows = row_count_result[0] if row_count_result else 0
                        
                        # Estimate table size (rough approximation)
                        # Try to get more accurate size estimate if possible
                        try:
                            # This is a rough estimate based on row count
                            table_bytes = table_rows * 150  # Assume ~150 bytes per row average
                        except:
                            table_bytes = table_rows * 100  # Fallback estimate
                        
                        estimated_rows += table_rows
                        estimated_bytes += table_bytes
                            
                    except Exception as e:
                        # If we can't get exact stats, make a reasonable estimate
                        try:
                            row_count = self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                            estimated_rows += row_count
                            estimated_bytes += row_count * 100  # Rough estimate: 100 bytes per row
                        except:
                            warnings.append(f"Could not estimate size for table: {table}")
            
            # Estimate execution time based on query complexity and data size
            estimated_time_ms = self._estimate_execution_time(clean_sql, estimated_rows, query_type)
            
            # Add query-specific warnings
            if query_type == "SELECT":
                if "SELECT *" in clean_sql.upper():
                    warnings.append("Consider specifying column names instead of SELECT * for better performance")
                if not re.search(r'\bLIMIT\b', clean_sql, re.IGNORECASE) and estimated_rows > 10000:
                    warnings.append(f"Query may return {estimated_rows:,} rows. Consider adding a LIMIT clause")
                if not re.search(r'\bWHERE\b', clean_sql, re.IGNORECASE) and estimated_rows > 1000:
                    warnings.append("Query scans entire table. Consider adding WHERE conditions to filter results")
            
            # Generate BigQuery-style suggestion message
            if valid:
                if estimated_bytes == 0:
                    suggestion = "This query will process 0 B when run."
                elif estimated_bytes < 1024:
                    suggestion = f"This query will process {estimated_bytes} B when run."
                elif estimated_bytes < 1024 * 1024:
                    suggestion = f"This query will process {estimated_bytes / 1024:.1f} KB when run."
                elif estimated_bytes < 1024 * 1024 * 1024:
                    suggestion = f"This query will process {estimated_bytes / (1024 * 1024):.1f} MB when run."
                else:
                    suggestion = f"This query will process {estimated_bytes / (1024 * 1024 * 1024):.1f} GB when run."
                
                if estimated_rows > 0:
                    suggestion += f" (≈{estimated_rows:,} rows scanned)"
            else:
                suggestion = "Query validation failed. Please check the syntax and try again."
            
            validation_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                "valid": valid,
                "estimated_bytes_processed": int(estimated_bytes),
                "estimated_rows_scanned": int(estimated_rows),
                "estimated_execution_time_ms": int(estimated_time_ms),
                "affected_tables": affected_tables,
                "query_type": query_type,
                "warnings": warnings,
                "errors": errors,
                "suggestion": suggestion,
                "validation_time_ms": int(validation_time)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "estimated_bytes_processed": 0,
                "estimated_rows_scanned": 0,
                "estimated_execution_time_ms": 0,
                "affected_tables": [],
                "query_type": "UNKNOWN",
                "warnings": warnings,
                "errors": [f"Validation error: {str(e)}"],
                "suggestion": "Query validation failed. Please check the syntax and try again."
            }
    
    def _get_query_type(self, sql: str) -> str:
        """Determine the type of SQL query"""
        sql_upper = sql.upper().strip()
        
        if sql_upper.startswith('SELECT'):
            return "SELECT"
        elif sql_upper.startswith('INSERT'):
            return "INSERT"
        elif sql_upper.startswith('UPDATE'):
            return "UPDATE"
        elif sql_upper.startswith('DELETE'):
            return "DELETE"
        elif sql_upper.startswith('CREATE'):
            return "CREATE"
        elif sql_upper.startswith('DROP'):
            return "DROP"
        elif sql_upper.startswith('ALTER'):
            return "ALTER"
        elif sql_upper.startswith('WITH'):
            return "WITH"
        else:
            return "OTHER"
    
    def _extract_table_names(self, sql: str) -> List[str]:
        """Extract table names from SQL query"""
        # Simple regex-based extraction (could be improved with a proper SQL parser)
        tables = set()
        
        # Look for patterns like "FROM table_name" and "JOIN table_name"
        from_pattern = r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(from_pattern, sql, re.IGNORECASE)
        tables.update(matches)
        
        # Look for table names after INSERT INTO, UPDATE, etc.
        insert_pattern = r'\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(insert_pattern, sql, re.IGNORECASE)
        tables.update(matches)
        
        update_pattern = r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(update_pattern, sql, re.IGNORECASE)
        tables.update(matches)
        
        return list(tables)
    
    def _estimate_execution_time(self, sql: str, estimated_rows: int, query_type: str) -> int:
        """Estimate query execution time in milliseconds"""
        base_time = 10  # Base overhead
        
        # Factor in data size
        if estimated_rows > 0:
            # Rough estimate: 0.001ms per row for simple queries
            base_time += estimated_rows * 0.001
        
        # Factor in query complexity
        sql_upper = sql.upper()
        
        # JOIN operations add overhead
        join_count = len(re.findall(r'\bJOIN\b', sql_upper))
        base_time += join_count * 50
        
        # GROUP BY adds overhead
        if 'GROUP BY' in sql_upper:
            base_time += estimated_rows * 0.01
        
        # ORDER BY adds overhead
        if 'ORDER BY' in sql_upper:
            base_time += estimated_rows * 0.005
        
        # Window functions add overhead
        window_functions = ['ROW_NUMBER', 'RANK', 'DENSE_RANK', 'LAG', 'LEAD', 'SUM(', 'COUNT(', 'AVG(', 'MIN(', 'MAX(']
        if any(func in sql_upper for func in window_functions) and 'OVER' in sql_upper:
            base_time += estimated_rows * 0.02
        
        # Subqueries add overhead
        subquery_count = sql.count('(') - sql.count(')')  # Rough estimate
        if subquery_count > 0:
            base_time += subquery_count * 100
        
        return max(10, int(base_time))  # Minimum 10ms

    async def cleanup(self):
        """Clean up resources"""
        if self.connection:
            self.connection.close()
            self.connection = None
        self.is_initialized = False
        print("🧹 DuckDB runner cleaned up")
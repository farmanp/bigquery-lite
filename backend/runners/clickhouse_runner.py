#!/usr/bin/env python3
"""
ClickHouse Runner

Handles query execution using ClickHouse for distributed OLAP processing.
Provides BigQuery-like functionality with distributed query execution.
"""

import time
import asyncio
import re
from typing import Dict, Any, Optional, List
import clickhouse_connect
from clickhouse_connect.driver.exceptions import ClickHouseError


class ClickHouseRunner:
    """ClickHouse query execution engine"""
    
    def __init__(self, host: str = None, port: int = None, 
                 username: str = None, password: str = None):
        # Use environment variables if available, otherwise default values
        import os
        self.host = host or os.getenv('CLICKHOUSE_HOST', 'localhost')
        self.port = port or int(os.getenv('CLICKHOUSE_PORT', '8123'))
        self.username = username or os.getenv('CLICKHOUSE_USER', 'admin')
        self.password = password or os.getenv('CLICKHOUSE_PASSWORD', 'password')
        self.client = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize ClickHouse connection and setup sample data"""
        try:
            # Create connection
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                connect_timeout=10,
                send_receive_timeout=30
            )
            
            # Test connection
            result = self.client.command("SELECT 1")
            if result != 1:
                raise Exception("Connection test failed")
            
            # Create database if it doesn't exist
            self.client.command("CREATE DATABASE IF NOT EXISTS bigquery_lite")
            self.client.command("USE bigquery_lite")
            
            # Setup sample tables
            await self._setup_sample_data()
            
            self.is_initialized = True
            print("✅ ClickHouse runner initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize ClickHouse: {e}")
            # Don't raise the exception to allow graceful degradation
            self.is_initialized = False
    
    async def _setup_sample_data(self):
        """Setup sample data in ClickHouse"""
        try:
            # Create NYC taxi table structure (compatible with DuckDB data)
            self.client.command("""
                CREATE TABLE IF NOT EXISTS nyc_taxi (
                    id UInt64,
                    payment_type String,
                    fare_amount Float64,
                    trip_distance Float64,
                    total_amount Float64,
                    passenger_count UInt8,
                    tpep_pickup_datetime DateTime,
                    tpep_dropoff_datetime DateTime,
                    tip_amount Float64
                ) ENGINE = MergeTree()
                ORDER BY (tpep_pickup_datetime, id)
            """)
            
            # Check if table is empty and populate with sample data
            count = self.client.command("SELECT count() FROM nyc_taxi")
            if count == 0:
                # Insert sample data
                self.client.command("""
                    INSERT INTO nyc_taxi 
                    SELECT 
                        number as id,
                        ['cash', 'credit_card', 'dispute', 'no_charge'][number % 4 + 1] as payment_type,
                        rand() % 50 + 5 as fare_amount,
                        rand() % 10 + 1 as trip_distance,
                        rand() % 60 + 10 as total_amount,
                        rand() % 5 + 1 as passenger_count,
                        now() - interval rand() % 2592000 second as tpep_pickup_datetime,
                        now() - interval rand() % 2592000 second + interval rand() % 7200 second as tpep_dropoff_datetime,
                        rand() % 10 as tip_amount
                    FROM numbers(10000)
                """)
                print("✅ Sample NYC taxi data created in ClickHouse")
            
            # Create additional sample table
            self.client.command("""
                CREATE TABLE IF NOT EXISTS sample_data (
                    id UInt64,
                    value Float64,
                    category String,
                    created_at DateTime
                ) ENGINE = MergeTree()
                ORDER BY (created_at, id)
            """)
            
            # Populate sample_data if empty
            count = self.client.command("SELECT count() FROM sample_data")
            if count == 0:
                self.client.command("""
                    INSERT INTO sample_data 
                    SELECT 
                        number as id,
                        rand() % 1000 as value,
                        concat('category_', toString(number % 5)) as category,
                        now() - interval rand() % 31536000 second as created_at
                    FROM numbers(5000)
                """)
                print("✅ Sample data created in ClickHouse")
            
        except Exception as e:
            print(f"⚠️  Failed to setup ClickHouse sample data: {e}")
    
    def _clean_sql_for_clickhouse(self, sql: str) -> str:
        """Clean SQL query for ClickHouse compatibility"""
        # Remove comments and normalize whitespace
        lines = []
        for line in sql.split('\n'):
            # Remove SQL comments
            line = line.split('--')[0].strip()
            if line:
                lines.append(line)
        
        # Join lines and clean up
        cleaned = ' '.join(lines)
        
        # Remove ALL semicolons (ClickHouse doesn't allow them)
        cleaned = cleaned.replace(';', '').strip()
        
        # Log the cleaned SQL for debugging
        print(f"🔍 Cleaned SQL for ClickHouse: {cleaned}")
        
        return cleaned
    
    async def execute_query(self, sql: str) -> Dict[str, Any]:
        """Execute a SQL query and return results with performance metrics"""
        
        if not self.is_initialized:
            await self.initialize()
            
        if not self.is_initialized:
            raise Exception("ClickHouse is not available")
        
        start_time = time.time()
        
        try:
            # Ensure we're using the correct database
            self.client.command("USE bigquery_lite")
            
            # Clean the SQL query for ClickHouse compatibility
            cleaned_sql = self._clean_sql_for_clickhouse(sql)
            
            # Execute the query
            result = self.client.query(cleaned_sql)
            
            execution_time = time.time() - start_time
            
            # Convert result to list of dictionaries
            if result.result_rows:
                # Get column names
                columns = [col[0] for col in result.column_names]
                
                # Convert rows to dictionaries
                data = []
                for row in result.result_rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        column_name = columns[i] if i < len(columns) else f"col_{i}"
                        
                        # Handle different data types for JSON serialization
                        if hasattr(value, 'isoformat'):  # datetime objects
                            row_dict[column_name] = value.isoformat()
                        elif isinstance(value, (int, float, str, bool)) or value is None:
                            row_dict[column_name] = value
                        else:
                            row_dict[column_name] = str(value)
                    
                    data.append(row_dict)
            else:
                data = []
            
            # Get query execution plan
            try:
                plan_sql = f"EXPLAIN {cleaned_sql}"
                plan_result = self.client.query(plan_sql)
                query_plan = "\n".join([str(row[0]) for row in plan_result.result_rows])
            except:
                query_plan = "Query plan not available"
            
            # Simulate performance metrics (ClickHouse provides detailed query logs
            # but for simplicity we'll simulate some metrics)
            row_count = len(data)
            estimated_memory = max(0.5, row_count * 0.002)  # Rough estimate
            
            return {
                "data": data,
                "execution_time": execution_time,
                "rows": row_count,
                "engine": "clickhouse",
                "query_plan": query_plan,
                "performance_metrics": {
                    "execution_time": execution_time,
                    "memory_used_mb": estimated_memory,
                    "rows_processed": row_count,
                    "engine": "clickhouse",
                    "cpu_time": execution_time * 0.6,    # Simulated
                    "io_wait": execution_time * 0.2,     # Simulated
                    "network_time": execution_time * 0.1  # Simulated distributed overhead
                }
            }
            
        except ClickHouseError as e:
            execution_time = time.time() - start_time
            
            return {
                "data": [],
                "execution_time": execution_time,
                "rows": 0,
                "engine": "clickhouse",
                "error": str(e),
                "query_plan": f"Error executing query: {str(e)}"
            }
        except Exception as e:
            execution_time = time.time() - start_time
            
            return {
                "data": [],
                "execution_time": execution_time,
                "rows": 0,
                "engine": "clickhouse",
                "error": str(e),
                "query_plan": f"Error executing query: {str(e)}"
            }
    
    async def get_status(self) -> str:
        """Get runner status"""
        if not self.client:
            return "not_connected"
        
        try:
            # Test connection with a simple query
            result = self.client.command("SELECT 1")
            return "available" if result == 1 else "error"
        except:
            return "error"
    
    async def get_schema_info(self) -> Dict[str, Any]:
        """Get information about available tables and schemas"""
        if not self.is_initialized:
            return {"engine": "clickhouse", "error": "Not initialized"}
        
        try:
            # Get table information
            tables_result = self.client.query("""
                SELECT name, engine 
                FROM system.tables 
                WHERE database = 'bigquery_lite'
            """)
            
            tables = {}
            for row in tables_result.result_rows:
                table_name, engine = row
                
                # Get column information for each table
                columns_result = self.client.query(f"""
                    SELECT name, type 
                    FROM system.columns 
                    WHERE database = 'bigquery_lite' AND table = '{table_name}'
                """)
                
                tables[table_name] = {
                    "engine": engine,
                    "columns": [{"name": col[0], "type": col[1]} for col in columns_result.result_rows]
                }
            
            return {
                "engine": "clickhouse",
                "host": f"{self.host}:{self.port}",
                "database": "bigquery_lite",
                "tables": tables
            }
            
        except Exception as e:
            return {
                "engine": "clickhouse",
                "error": str(e)
            }
    
    async def get_cluster_info(self) -> Dict[str, Any]:
        """Get ClickHouse cluster information"""
        if not self.is_initialized:
            return {"error": "Not initialized"}
        
        try:
            # Get cluster information if available
            clusters_result = self.client.query("SELECT * FROM system.clusters")
            
            clusters = []
            for row in clusters_result.result_rows:
                clusters.append({
                    "cluster": row[0],
                    "shard_num": row[1],
                    "replica_num": row[2],
                    "host_name": row[3],
                    "port": row[4]
                })
            
            # Get current server info
            server_info = self.client.query("SELECT version(), hostName(), uptime()").result_rows[0]
            
            return {
                "engine": "clickhouse",
                "version": server_info[0],
                "hostname": server_info[1],
                "uptime": server_info[2],
                "clusters": clusters
            }
            
        except Exception as e:
            return {
                "engine": "clickhouse",
                "error": str(e)
            }
    
    async def validate_query(self, sql: str) -> Dict[str, Any]:
        """Validate query and estimate data processing without execution"""
        
        if not self.is_initialized:
            await self.initialize()
            
        if not self.is_initialized:
            return {
                "valid": False,
                "estimated_bytes_processed": 0,
                "estimated_rows_scanned": 0,
                "estimated_execution_time_ms": 0,
                "affected_tables": [],
                "query_type": "UNKNOWN",
                "warnings": [],
                "errors": ["ClickHouse is not available"],
                "suggestion": "ClickHouse connection failed. Please check the connection settings."
            }
        
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
            
            # Clean SQL for ClickHouse
            clean_sql = self._clean_sql_for_clickhouse(clean_sql)
            
            # Determine query type
            query_type = self._get_query_type(clean_sql)
            
            # Extract table names from query
            affected_tables = self._extract_table_names(clean_sql)
            
            # Use EXPLAIN to validate query without execution
            try:
                self.client.command("USE bigquery_lite")
                explain_result = self.client.query(f"EXPLAIN {clean_sql}")
                valid = True
            except Exception as e:
                errors.append(str(e))
                valid = False
                explain_result = None
            
            # Estimate data size for each table
            estimated_bytes = 0
            estimated_rows = 0
            
            if valid and affected_tables:
                for table in affected_tables:
                    try:
                        # Get table statistics from ClickHouse system tables
                        stats_result = self.client.query(f"""
                            SELECT 
                                total_rows,
                                total_bytes
                            FROM system.tables 
                            WHERE database = 'bigquery_lite' AND name = '{table}'
                        """)
                        
                        if stats_result.result_rows:
                            table_rows = stats_result.result_rows[0][0] or 0
                            table_bytes = stats_result.result_rows[0][1] or table_rows * 100
                            
                            estimated_rows += table_rows
                            estimated_bytes += table_bytes
                        else:
                            warnings.append(f"Table '{table}' not found or no statistics available")
                            
                    except Exception as e:
                        warnings.append(f"Could not estimate size for table '{table}': {str(e)}")
            
            # Estimate execution time based on query complexity and data size
            estimated_time_ms = self._estimate_execution_time(clean_sql, estimated_rows, query_type)
            
            # Add ClickHouse-specific warnings
            if query_type == "SELECT":
                if "SELECT *" in clean_sql.upper():
                    warnings.append("Consider specifying column names instead of SELECT * for better performance")
                if not re.search(r'\bLIMIT\b', clean_sql, re.IGNORECASE) and estimated_rows > 10000:
                    warnings.append(f"Query may return {estimated_rows:,} rows. Consider adding a LIMIT clause")
                if not re.search(r'\bWHERE\b', clean_sql, re.IGNORECASE) and estimated_rows > 1000:
                    warnings.append("Query scans entire table. Consider adding WHERE conditions for better performance")
            
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
        base_time = 20  # Base overhead (higher for distributed system)
        
        # Factor in data size
        if estimated_rows > 0:
            # ClickHouse is typically faster for OLAP workloads
            base_time += estimated_rows * 0.0005
        
        # Factor in query complexity
        sql_upper = sql.upper()
        
        # JOIN operations add overhead
        join_count = len(re.findall(r'\bJOIN\b', sql_upper))
        base_time += join_count * 30
        
        # GROUP BY adds overhead (but ClickHouse is optimized for this)
        if 'GROUP BY' in sql_upper:
            base_time += estimated_rows * 0.005
        
        # ORDER BY adds overhead
        if 'ORDER BY' in sql_upper:
            base_time += estimated_rows * 0.003
        
        # Window functions add overhead
        window_functions = ['ROW_NUMBER', 'RANK', 'DENSE_RANK', 'LAG', 'LEAD', 'SUM(', 'COUNT(', 'AVG(', 'MIN(', 'MAX(']
        if any(func in sql_upper for func in window_functions) and 'OVER' in sql_upper:
            base_time += estimated_rows * 0.01
        
        # Subqueries add overhead
        subquery_count = sql.count('(') - sql.count(')')  # Rough estimate
        if subquery_count > 0:
            base_time += subquery_count * 50
        
        return max(20, int(base_time))  # Minimum 20ms

    async def cleanup(self):
        """Clean up resources"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None
        self.is_initialized = False
        print("🧹 ClickHouse runner cleaned up")
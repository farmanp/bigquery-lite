#!/usr/bin/env python3
"""BigQuery-Lite CLI tool."""

import json
import os
from pathlib import Path
from typing import List, Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

app = typer.Typer(
    name="bqlite",
    help="BigQuery-Lite CLI tool for schema management and data ingestion",
    no_args_is_help=True,
)

console = Console()

# Default backend URL
DEFAULT_BACKEND_URL = "http://localhost:8002"


def get_backend_url() -> str:
    """Get backend URL from environment or use default."""
    return os.getenv("BQLITE_BACKEND_URL", DEFAULT_BACKEND_URL)


def handle_http_error(response: httpx.Response) -> None:
    """Handle HTTP errors with user-friendly messages."""
    if response.status_code == 404:
        rprint(f"[red]Error: Resource not found[/red]")
    elif response.status_code == 400:
        error_detail = response.json().get("detail", "Bad request")
        rprint(f"[red]Error: {error_detail}[/red]")
    elif response.status_code == 422:
        error_detail = response.json().get("detail", "Validation error")
        rprint(f"[red]Validation Error: {error_detail}[/red]")
    elif response.status_code >= 500:
        rprint(f"[red]Server Error: Backend service unavailable[/red]")
    else:
        rprint(f"[red]HTTP Error {response.status_code}: {response.text}[/red]")


@app.command("register")
def register_schema(
    proto_path: str = typer.Argument(..., help="Path to .proto file"),
    table: str = typer.Option(..., "--table", help="Target table name"),
    database: str = typer.Option("bigquery_lite", "--database", help="Target database name"),
    backend_url: str = typer.Option(None, "--backend-url", help="Backend URL"),
):
    """Register a protobuf schema from a .proto file."""
    backend_url = backend_url or get_backend_url()
    
    # Validate proto file exists
    proto_file = Path(proto_path)
    if not proto_file.exists():
        rprint(f"[red]Error: Proto file not found: {proto_path}[/red]")
        raise typer.Exit(1)
    
    if not proto_file.suffix == ".proto":
        rprint(f"[red]Error: File must have .proto extension[/red]")
        raise typer.Exit(1)
    
    try:
        with httpx.Client(timeout=30.0) as client:
            with open(proto_file, "rb") as f:
                files = {"proto_file": (proto_file.name, f, "text/plain")}
                data = {
                    "table_name": table,
                    "database_name": database
                }
                
                response = client.post(
                    f"{backend_url}/schemas/register",
                    files=files,
                    data=data
                )
        
        if response.status_code == 200:
            result = response.json()
            rprint(f"[green]✅ Schema registered successfully![/green]")
            rprint(f"Schema ID: {result['schema_id']}")
            rprint(f"Table: {result['database_name']}.{result['table_name']}")
            rprint(f"Fields: {result['field_count']}")
            rprint(f"Version: {result['version_hash'][:8]}")
        else:
            handle_http_error(response)
            raise typer.Exit(1)
            
    except httpx.ConnectError:
        rprint(f"[red]Error: Cannot connect to backend at {backend_url}[/red]")
        rprint("Make sure the backend service is running.")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command("create-table")
def create_table(
    table: str = typer.Argument(..., help="Table name (must be registered)"),
    engines: str = typer.Option("duckdb", "--engines", help="Comma-separated list of engines (duckdb,clickhouse)"),
    database: str = typer.Option("bigquery_lite", "--database", help="Database name"),
    if_not_exists: bool = typer.Option(True, "--if-not-exists/--replace", help="Use IF NOT EXISTS clause"),
    flattened_view: bool = typer.Option(False, "--flattened-view", help="Create flattened view for nested schemas"),
    backend_url: str = typer.Option(None, "--backend-url", help="Backend URL"),
):
    """Create tables from a registered schema."""
    backend_url = backend_url or get_backend_url()
    
    # Parse engines list
    engine_list = [e.strip() for e in engines.split(",")]
    valid_engines = {"duckdb", "clickhouse"}
    invalid_engines = set(engine_list) - valid_engines
    if invalid_engines:
        rprint(f"[red]Error: Invalid engines: {', '.join(invalid_engines)}[/red]")
        rprint(f"Valid engines: {', '.join(valid_engines)}")
        raise typer.Exit(1)
    
    try:
        # First, find the schema ID for the given table
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{backend_url}/schemas")
            
        if response.status_code != 200:
            handle_http_error(response)
            raise typer.Exit(1)
            
        schemas = response.json()["schemas"]
        matching_schema = None
        for schema in schemas:
            if schema["table_name"] == table and schema["database_name"] == database:
                matching_schema = schema
                break
        
        if not matching_schema:
            rprint(f"[red]Error: No registered schema found for table '{database}.{table}'[/red]")
            rprint("Use 'bqlite list-schemas' to see available schemas.")
            raise typer.Exit(1)
        
        schema_id = matching_schema["schema_id"]
        
        # Create tables
        with httpx.Client(timeout=30.0) as client:
            request_data = {
                "engines": engine_list,
                "if_not_exists": if_not_exists,
                "create_flattened_view": flattened_view
            }
            
            response = client.post(
                f"{backend_url}/schemas/{schema_id}/tables/create",
                json=request_data
            )
        
        if response.status_code == 200:
            result = response.json()
            rprint(f"[green]✅ Table creation completed![/green]")
            
            # Display results table
            table_display = Table(title=f"Table Creation Results: {result['table_name']}")
            table_display.add_column("Engine", style="cyan")
            table_display.add_column("Status", style="green")
            table_display.add_column("Execution Time", style="yellow")
            table_display.add_column("Error", style="red")
            
            for engine, engine_result in result["results"].items():
                status = "✅ Success" if engine_result["success"] else "❌ Failed"
                exec_time = f"{engine_result.get('execution_time', 0):.3f}s"
                error = engine_result.get("error") or ""
                table_display.add_row(engine, status, exec_time, error[:50])
            
            console.print(table_display)
            
            if result["flattened_view_created"]:
                rprint(f"[green]📊 Flattened view created for nested schema[/green]")
            
            rprint(f"\nSummary: {result['successful_engines']}/{result['total_engines']} engines successful")
        else:
            handle_http_error(response)
            raise typer.Exit(1)
            
    except httpx.ConnectError:
        rprint(f"[red]Error: Cannot connect to backend at {backend_url}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command("ingest")
def ingest_data(
    data_path: str = typer.Argument(..., help="Path to protobuf data file (.pb)"),
    schema: str = typer.Option(..., "--schema", help="Schema name (table name)"),
    engine: str = typer.Option("duckdb", "--engine", help="Target engine (duckdb or clickhouse)"),
    database: str = typer.Option("bigquery_lite", "--database", help="Database name"),
    batch_size: int = typer.Option(1000, "--batch-size", help="Batch size for insertion"),
    create_table: bool = typer.Option(True, "--create-table/--no-create-table", help="Create table if not exists"),
    backend_url: str = typer.Option(None, "--backend-url", help="Backend URL"),
):
    """Ingest protobuf data using a registered schema."""
    backend_url = backend_url or get_backend_url()
    
    # Validate data file exists
    data_file = Path(data_path)
    if not data_file.exists():
        rprint(f"[red]Error: Data file not found: {data_path}[/red]")
        raise typer.Exit(1)
    
    if not data_file.suffix == ".pb":
        rprint(f"[red]Error: File must have .pb extension[/red]")
        raise typer.Exit(1)
    
    try:
        # Find schema ID
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{backend_url}/schemas")
            
        if response.status_code != 200:
            handle_http_error(response)
            raise typer.Exit(1)
            
        schemas = response.json()["schemas"]
        matching_schema = None
        for schema_info in schemas:
            if schema_info["table_name"] == schema and schema_info["database_name"] == database:
                matching_schema = schema_info
                break
        
        if not matching_schema:
            rprint(f"[red]Error: No registered schema found for table '{database}.{schema}'[/red]")
            raise typer.Exit(1)
        
        schema_id = matching_schema["schema_id"]
        
        # Ingest data
        with httpx.Client(timeout=300.0) as client:  # Longer timeout for data ingestion
            with open(data_file, "rb") as f:
                files = {"pb_file": (data_file.name, f, "application/octet-stream")}
                data = {
                    "target_engine": engine,
                    "batch_size": batch_size,
                    "create_table_if_not_exists": create_table
                }
                
                rprint(f"[blue]🔄 Ingesting data from {data_file.name}...[/blue]")
                response = client.post(
                    f"{backend_url}/schemas/{schema_id}/ingest",
                    files=files,
                    data=data
                )
        
        if response.status_code == 200:
            result = response.json()
            if result["status"] == "completed":
                rprint(f"[green]✅ Data ingestion completed successfully![/green]")
            elif result["status"] == "partial":
                rprint(f"[yellow]⚠️ Data ingestion partially successful[/yellow]")
            else:
                rprint(f"[red]❌ Data ingestion failed[/red]")
            
            rprint(f"Job ID: {result['job_id']}")
            rprint(f"Records processed: {result['records_processed']}")
            rprint(f"Records inserted: {result['records_inserted']}")
            rprint(f"Processing time: {result['processing_time']:.3f}s")
            
            if result["errors"]:
                rprint(f"[yellow]Errors encountered: {len(result['errors'])}[/yellow]")
                for i, error in enumerate(result["errors"][:3]):  # Show first 3 errors
                    rprint(f"  {i+1}. {error}")
                if len(result["errors"]) > 3:
                    rprint(f"  ... and {len(result['errors']) - 3} more errors")
        else:
            handle_http_error(response)
            raise typer.Exit(1)
            
    except httpx.ConnectError:
        rprint(f"[red]Error: Cannot connect to backend at {backend_url}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-schemas")
def list_schemas(
    backend_url: str = typer.Option(None, "--backend-url", help="Backend URL"),
):
    """List all registered schemas."""
    backend_url = backend_url or get_backend_url()
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{backend_url}/schemas")
        
        if response.status_code == 200:
            result = response.json()
            schemas = result["schemas"]
            
            if not schemas:
                rprint("[yellow]No schemas registered yet.[/yellow]")
                return
            
            # Display schemas table
            table = Table(title=f"Registered Schemas ({result['total']} total)")
            table.add_column("Schema ID", style="cyan")
            table.add_column("Table", style="green")
            table.add_column("Database", style="blue")
            table.add_column("Fields", style="yellow")
            table.add_column("Versions", style="magenta")
            table.add_column("Created", style="dim")
            
            for schema in schemas:
                schema_id_short = schema["schema_id"][:8] + "..."
                created_date = schema["created_at"][:10]  # Just the date part
                table.add_row(
                    schema_id_short,
                    schema["table_name"],
                    schema["database_name"],
                    str(schema["field_count"]),
                    str(schema["total_versions"]),
                    created_date
                )
            
            console.print(table)
        else:
            handle_http_error(response)
            raise typer.Exit(1)
            
    except httpx.ConnectError:
        rprint(f"[red]Error: Cannot connect to backend at {backend_url}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
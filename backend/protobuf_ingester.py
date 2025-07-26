#!/usr/bin/env python3
"""
Protobuf Data Ingester for BigQuery-Lite

Handles decoding of protobuf-encoded data files using registered schemas
and bulk ingestion into DuckDB/ClickHouse databases.
"""

import os
import json
import tempfile
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Iterator
from pathlib import Path
import logging

import google.protobuf.message
from google.protobuf.descriptor import Descriptor
from google.protobuf.json_format import MessageToDict
from google.protobuf import message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProtobufDecodingError(Exception):
    """Exception for protobuf decoding errors"""
    pass


class ProtobufIngestionError(Exception):
    """Exception for protobuf ingestion errors"""
    pass


class ProtobufIngester:
    """
    Handles protobuf data decoding and database ingestion.
    
    Responsibilities:
    1. Compile .proto files to generate Python classes
    2. Decode binary protobuf messages using compiled schema
    3. Convert protobuf messages to database-compatible records
    4. Bulk insert records into target database engines
    """
    
    def __init__(self, protoc_path: str = "protoc"):
        """
        Initialize the Protobuf Ingester
        
        Args:
            protoc_path: Path to protoc binary (default: "protoc" from PATH)
        """
        self.protoc_path = protoc_path
        self._validate_protoc_installation()
    
    def _validate_protoc_installation(self) -> None:
        """Validate that protoc is available"""
        try:
            result = subprocess.run([self.protoc_path, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.warning(f"protoc not found or not working: {result.stderr}")
                return
            
            logger.info(f"protoc found: {result.stdout.strip()}")
            
        except subprocess.TimeoutExpired:
            logger.warning("protoc command timed out")
        except FileNotFoundError:
            raise ProtobufDecodingError(f"protoc binary not found at {self.protoc_path}")
    
    def _compile_proto_to_python(self, proto_content: str) -> Tuple[str, str]:
        """
        Compile protobuf schema to Python classes
        
        Args:
            proto_content: Content of the .proto file
            
        Returns:
            Tuple of (python_module_path, message_class_name)
            
        Raises:
            ProtobufDecodingError: If compilation fails
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Write proto file
            proto_file = temp_dir_path / "schema.proto"
            proto_file.write_text(proto_content)
            
            # Create output directory for Python files
            python_out_dir = temp_dir_path / "python_out"
            python_out_dir.mkdir()
            
            # Compile proto to Python
            cmd = [
                self.protoc_path,
                f"--proto_path={temp_dir_path}",
                f"--python_out={python_out_dir}",
                str(proto_file)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Unknown protoc error"
                    raise ProtobufDecodingError(f"protoc compilation failed: {error_msg}")
                
                # Find generated Python file
                python_files = list(python_out_dir.glob("*_pb2.py"))
                if not python_files:
                    raise ProtobufDecodingError("No Python protobuf file generated")
                
                python_file = python_files[0]
                
                # Copy the generated file to a persistent location for import
                # Note: In a real implementation, you'd want to manage this better
                persistent_dir = Path("/tmp/bigquery_lite_proto_modules")
                persistent_dir.mkdir(exist_ok=True)
                
                persistent_file = persistent_dir / python_file.name
                persistent_file.write_text(python_file.read_text())
                
                # Extract message class name from proto content
                message_class_name = self._extract_message_class_name(proto_content)
                
                return str(persistent_file), message_class_name
                
            except subprocess.TimeoutExpired:
                raise ProtobufDecodingError("protoc compilation timed out")
    
    def _extract_message_class_name(self, proto_content: str) -> str:
        """
        Extract the main message class name from proto content
        
        Args:
            proto_content: Content of the .proto file
            
        Returns:
            Name of the main message class
        """
        # Simple parsing - look for the first message declaration
        lines = proto_content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('message ') and '{' in line:
                # Extract message name
                message_name = line.replace('message ', '').replace(' {', '').strip()
                return message_name
        
        raise ProtobufDecodingError("No message definition found in proto file")
    
    def _load_protobuf_class(self, python_module_path: str, message_class_name: str):
        """
        Dynamically load protobuf message class from compiled Python module
        
        Args:
            python_module_path: Path to compiled Python module
            message_class_name: Name of the message class
            
        Returns:
            Protobuf message class
        """
        import sys
        import importlib.util
        
        try:
            # Load module
            module_name = Path(python_module_path).stem
            spec = importlib.util.spec_from_file_location(module_name, python_module_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Get message class
            if not hasattr(module, message_class_name):
                raise ProtobufDecodingError(f"Message class {message_class_name} not found in module")
            
            return getattr(module, message_class_name)
            
        except Exception as e:
            raise ProtobufDecodingError(f"Failed to load protobuf class: {e}")
    
    def decode_protobuf_messages(self, 
                                proto_content: str,
                                pb_data: bytes) -> List[Dict[str, Any]]:
        """
        Decode protobuf messages from binary data using schema
        
        Args:
            proto_content: Content of the .proto file
            pb_data: Binary protobuf data (one message per line)
            
        Returns:
            List of decoded message dictionaries
            
        Raises:
            ProtobufDecodingError: If decoding fails
        """
        try:
            # Compile proto to Python classes
            python_module_path, message_class_name = self._compile_proto_to_python(proto_content)
            
            # Load protobuf message class
            message_class = self._load_protobuf_class(python_module_path, message_class_name)
            
            # Decode messages (assuming one message per line)
            decoded_messages = []
            lines = pb_data.split(b'\n')
            
            for line_num, line in enumerate(lines, 1):
                if not line.strip():  # Skip empty lines
                    continue
                
                try:
                    # Create message instance and parse binary data
                    message_instance = message_class()
                    message_instance.ParseFromString(line.strip())
                    
                    # Convert to dictionary using MessageToDict for better handling
                    # of repeated fields and nested messages
                    message_dict = MessageToDict(message_instance)
                    
                    # Add metadata
                    message_dict['_line_number'] = line_num
                    message_dict['_ingestion_timestamp'] = datetime.now().isoformat()
                    
                    decoded_messages.append(message_dict)
                    
                except Exception as e:
                    logger.warning(f"Failed to decode message at line {line_num}: {e}")
                    # Continue processing other messages
                    continue
            
            logger.info(f"Successfully decoded {len(decoded_messages)} protobuf messages")
            return decoded_messages
            
        except Exception as e:
            raise ProtobufDecodingError(f"Failed to decode protobuf messages: {e}")
    
    def prepare_records_for_insertion(self,
                                    decoded_messages: List[Dict[str, Any]],
                                    schema_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare decoded protobuf messages for database insertion
        
        Args:
            decoded_messages: List of decoded message dictionaries
            schema_fields: BigQuery schema field definitions
            
        Returns:
            List of database-ready records
        """
        prepared_records = []
        
        # Create field type mapping for data conversion
        field_types = {}
        for field in schema_fields:
            field_types[field['name']] = field['type']
        
        for message in decoded_messages:
            prepared_record = {}
            
            # Convert each field according to schema
            for field_name, field_type in field_types.items():
                if field_name in message:
                    value = message[field_name]
                    prepared_record[field_name] = self._convert_field_value(value, field_type)
                else:
                    # Handle missing fields with defaults
                    prepared_record[field_name] = self._get_default_value(field_type)
            
            # Add metadata fields
            prepared_record['_line_number'] = message.get('_line_number')
            prepared_record['_ingestion_timestamp'] = message.get('_ingestion_timestamp')
            
            prepared_records.append(prepared_record)
        
        return prepared_records
    
    def _convert_field_value(self, value: Any, field_type: str) -> Any:
        """
        Convert protobuf field value to database-compatible type
        
        Args:
            value: Raw protobuf field value
            field_type: BigQuery field type
            
        Returns:
            Converted value suitable for database insertion
        """
        if value is None:
            return None
        
        # Handle different BigQuery field types
        if field_type == 'STRING':
            return str(value)
        elif field_type == 'INTEGER':
            return int(value) if isinstance(value, (int, float, str)) else value
        elif field_type == 'FLOAT':
            return float(value) if isinstance(value, (int, float, str)) else value
        elif field_type == 'BOOLEAN':
            return bool(value)
        elif field_type == 'TIMESTAMP':
            # Handle timestamp conversion
            if isinstance(value, str):
                return value
            elif isinstance(value, (int, float)):
                return datetime.fromtimestamp(value).isoformat()
            else:
                return str(value)
        elif field_type == 'RECORD':
            # For nested records, convert to JSON string
            return json.dumps(value) if isinstance(value, dict) else str(value)
        elif field_type == 'REPEATED':
            # For repeated fields, convert to JSON array
            return json.dumps(value) if isinstance(value, list) else str(value)
        else:
            # Default: convert to string
            return str(value)
    
    def _get_default_value(self, field_type: str) -> Any:
        """
        Get default value for missing fields based on type
        
        Args:
            field_type: BigQuery field type
            
        Returns:
            Default value for the field type
        """
        defaults = {
            'STRING': '',
            'INTEGER': 0,
            'FLOAT': 0.0,
            'BOOLEAN': False,
            'TIMESTAMP': datetime.now().isoformat(),
            'RECORD': '{}',
            'REPEATED': '[]'
        }
        return defaults.get(field_type, None)
    
    async def ingest_to_database(self,
                               prepared_records: List[Dict[str, Any]],
                               table_name: str,
                               database_name: str,
                               engine_runner,
                               batch_size: int = 1000) -> Tuple[int, List[str]]:
        """
        Ingest prepared records into database
        
        Args:
            prepared_records: List of database-ready records
            table_name: Target table name
            database_name: Target database name
            engine_runner: Database engine runner instance
            batch_size: Batch size for bulk inserts
            
        Returns:
            Tuple of (records_inserted, list_of_errors)
        """
        if not prepared_records:
            return 0, []
        
        inserted_count = 0
        errors = []
        
        # Process records in batches
        for i in range(0, len(prepared_records), batch_size):
            batch = prepared_records[i:i + batch_size]
            
            try:
                # Generate INSERT SQL for batch
                insert_sql = self._generate_bulk_insert_sql(
                    batch, table_name, database_name
                )
                
                # Execute insert
                result = await engine_runner.execute_query(insert_sql)
                
                if "error" in result:
                    errors.append(f"Batch {i//batch_size + 1}: {result['error']}")
                else:
                    inserted_count += len(batch)
                    logger.info(f"Inserted batch {i//batch_size + 1} with {len(batch)} records")
                
            except Exception as e:
                error_msg = f"Batch {i//batch_size + 1}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Failed to insert batch: {error_msg}")
        
        return inserted_count, errors
    
    def _generate_bulk_insert_sql(self,
                                records: List[Dict[str, Any]],
                                table_name: str,
                                database_name: str) -> str:
        """
        Generate bulk INSERT SQL for records
        
        Args:
            records: List of records to insert
            table_name: Target table name
            database_name: Target database name
            
        Returns:
            SQL INSERT statement
        """
        if not records:
            return ""
        
        # Get column names from first record
        columns = list(records[0].keys())
        column_names = ', '.join([f'"{col}"' for col in columns])
        
        # Generate VALUES clauses
        values_clauses = []
        for record in records:
            values = []
            for col in columns:
                value = record.get(col)
                if value is None:
                    values.append('NULL')
                elif isinstance(value, str):
                    # Escape single quotes
                    escaped_value = value.replace("'", "''")
                    values.append(f"'{escaped_value}'")
                elif isinstance(value, bool):
                    values.append('TRUE' if value else 'FALSE')
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                else:
                    # Convert to string and escape
                    str_value = str(value).replace("'", "''")
                    values.append(f"'{str_value}'")
            
            values_clauses.append(f"({', '.join(values)})")
        
        # Combine into INSERT statement
        insert_sql = f"""
            INSERT INTO {database_name}.{table_name} ({column_names})
            VALUES {', '.join(values_clauses)}
        """
        
        return insert_sql
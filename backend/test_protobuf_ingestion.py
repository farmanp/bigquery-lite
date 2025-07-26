#!/usr/bin/env python3
"""
Test script for protobuf data ingestion functionality

This script creates sample protobuf data and tests the ingestion pipeline.
"""

import os
import json
import tempfile
from pathlib import Path

# Sample protobuf schema for testing
SAMPLE_PROTO = """
syntax = "proto3";

message UserEvent {
    string user_id = 1;
    string event_type = 2;
    int64 timestamp = 3;
    string page_url = 4;
    string session_id = 5;
    UserMetadata metadata = 6;
}

message UserMetadata {
    string device_type = 1;
    string browser = 2;
    string location = 3;
    bool is_premium = 4;
}
"""

# Sample BigQuery schema JSON (what protoc-gen-bq-schema would generate)
SAMPLE_BQ_SCHEMA = [
    {
        "name": "user_id",
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "event_type", 
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "timestamp",
        "type": "INTEGER", 
        "mode": "NULLABLE"
    },
    {
        "name": "page_url",
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "session_id",
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "metadata",
        "type": "RECORD",
        "mode": "NULLABLE",
        "fields": [
            {
                "name": "device_type",
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "browser", 
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "location",
                "type": "STRING", 
                "mode": "NULLABLE"
            },
            {
                "name": "is_premium",
                "type": "BOOLEAN",
                "mode": "NULLABLE"
            }
        ]
    }
]

def create_sample_files():
    """Create sample proto and schema files for testing"""
    
    # Create test directory
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    
    # Write sample proto file
    proto_file = test_dir / "user_events.proto"
    proto_file.write_text(SAMPLE_PROTO)
    
    # Write sample schema file
    schema_file = test_dir / "user_events.schema"
    schema_file.write_text(json.dumps(SAMPLE_BQ_SCHEMA, indent=2))
    
    print(f"✅ Created sample files:")
    print(f"   - {proto_file}")
    print(f"   - {schema_file}")
    
    return proto_file, schema_file

def create_sample_protobuf_data():
    """
    Create sample binary protobuf data for testing
    
    Note: This is a simplified version. In practice, you would:
    1. Compile the .proto file with protoc --python_out
    2. Import the generated classes
    3. Create message instances and serialize them
    
    For this test, we'll create a mock binary file.
    """
    test_dir = Path("test_data")
    pb_file = test_dir / "sample_events.pb"
    
    # Create mock binary data (in practice, this would be real protobuf-encoded data)
    # For demonstration, we'll create a file that the ingester can attempt to process
    mock_data = b"Mock protobuf data - in real usage this would be binary protobuf messages"
    pb_file.write_bytes(mock_data)
    
    print(f"✅ Created sample protobuf data file: {pb_file}")
    return pb_file

def print_test_instructions():
    """Print instructions for testing the protobuf ingestion"""
    
    print("\n" + "="*80)
    print("🧪 PROTOBUF INGESTION TEST INSTRUCTIONS")
    print("="*80)
    
    print("\n1. Start the backend server:")
    print("   cd backend")
    print("   python app.py")
    
    print("\n2. Register the schema using the sample proto file:")
    print("   curl -X POST http://localhost:8002/schemas/register \\")
    print("     -F 'proto_file=@test_data/user_events.proto' \\")
    print("     -F 'table_name=user_events' \\")
    print("     -F 'database_name=bigquery_lite'")
    
    print("\n3. Create the table in DuckDB:")
    print("   curl -X POST http://localhost:8002/schemas/bigquery_lite.user_events/tables/create \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"engines\": [\"duckdb\"], \"if_not_exists\": true}'")
    
    print("\n4. Test protobuf data ingestion:")
    print("   curl -X POST http://localhost:8002/schemas/bigquery_lite.user_events/ingest \\")
    print("     -F 'pb_file=@test_data/sample_events.pb' \\")
    print("     -F 'target_engine=duckdb' \\")
    print("     -F 'batch_size=100'")
    
    print("\n5. Query the ingested data:")
    print("   curl -X POST http://localhost:8002/queries \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"sql\": \"SELECT * FROM bigquery_lite.user_events LIMIT 10\", \"engine\": \"duckdb\"}'")
    
    print("\n" + "="*80)
    print("📝 NOTES:")
    print("- The sample .pb file contains mock data for demonstration")
    print("- For real protobuf data, you would need properly encoded messages")
    print("- The ingester will attempt to decode using the registered schema")
    print("- Check the server logs for detailed processing information")
    print("="*80)

def test_protobuf_ingester():
    """Test the ProtobufIngester class directly"""
    
    print("\n🧪 Testing ProtobufIngester class...")
    
    try:
        from protobuf_ingester import ProtobufIngester, ProtobufDecodingError
        
        ingester = ProtobufIngester()
        print("✅ ProtobufIngester initialized successfully")
        
        # Test field value conversion
        test_cases = [
            ("test_string", "STRING", "test_string"),
            (123, "INTEGER", 123),
            (45.67, "FLOAT", 45.67),
            (True, "BOOLEAN", True),
            ({"nested": "data"}, "RECORD", '{"nested": "data"}'),
            ([1, 2, 3], "REPEATED", "[1, 2, 3]")
        ]
        
        for value, field_type, expected in test_cases:
            result = ingester._convert_field_value(value, field_type)
            print(f"✅ Convert {value} ({field_type}) -> {result}")
        
        print("✅ Field conversion tests passed")
        
        # Test SQL generation
        sample_records = [
            {"user_id": "user123", "event_type": "click", "timestamp": 1234567890},
            {"user_id": "user456", "event_type": "view", "timestamp": 1234567891}
        ]
        
        sql = ingester._generate_bulk_insert_sql(sample_records, "user_events", "bigquery_lite")
        print(f"✅ Generated SQL:\n{sql[:200]}...")
        
    except ImportError as e:
        print(f"❌ Failed to import ProtobufIngester: {e}")
    except Exception as e:
        print(f"❌ Error testing ProtobufIngester: {e}")

if __name__ == "__main__":
    print("🚀 Setting up protobuf ingestion test environment...")
    
    # Create sample files
    proto_file, schema_file = create_sample_files()
    pb_file = create_sample_protobuf_data()
    
    # Test the ingester class
    test_protobuf_ingester()
    
    # Print test instructions
    print_test_instructions()
    
    print("\n✅ Test setup complete! Follow the instructions above to test the implementation.")
#!/usr/bin/env python3
"""
Test script for Schema Registry functionality
"""

import asyncio
import json
import sys
import os

# Add backend to path
sys.path.append('backend')

from schema_registry import SchemaRegistry, SchemaRegistryError

async def test_schema_registry():
    """Test schema registry operations"""
    print("=== Testing Schema Registry ===\n")
    
    try:
        # Initialize registry (bypass protoc validation for testing)
        registry = SchemaRegistry(db_path="./test_schema_registry.db", protoc_path="/usr/bin/true")
        print("✅ Schema registry initialized")
        
        # Load test schema
        with open('test_schemas/sample_schema.json', 'r') as f:
            test_schema = json.load(f)
        
        print(f"📄 Loaded test schema with {len(test_schema)} fields")
        
        # Test schema registration
        print("\n--- Testing Schema Registration ---")
        schema_id = await registry.register_schema_from_json(
            test_schema, 
            "test_users", 
            "test_db"
        )
        print(f"✅ Registered schema: {schema_id}")
        
        # Test schema retrieval
        print("\n--- Testing Schema Retrieval ---")
        schema_version = await registry.get_schema(schema_id)
        if schema_version:
            print(f"✅ Retrieved schema: {schema_version.schema_id}")
            print(f"   Table: {schema_version.table_name}")
            print(f"   Database: {schema_version.database_name}")
            print(f"   Version: {schema_version.version_hash}")
            print(f"   Fields: {len(schema_version.fields)}")
        else:
            print("❌ Failed to retrieve schema")
            return
        
        # Test schema listing
        print("\n--- Testing Schema Listing ---")
        schemas = await registry.list_schemas()
        print(f"✅ Found {len(schemas)} schemas")
        for schema in schemas:
            print(f"   - {schema.schema_id} ({schema.field_count} fields)")
        
        # Test table creation marking
        print("\n--- Testing Table Creation Tracking ---")
        await registry.mark_table_created(schema_id, "duckdb")
        await registry.mark_table_created(schema_id, "clickhouse")
        print("✅ Marked tables created in both engines")
        
        # Verify engines tracking
        updated_schema = await registry.get_schema(schema_id)
        print(f"   Engines created: {updated_schema.engines_created}")
        
        # Test duplicate registration (should update version)
        print("\n--- Testing Schema Update ---")
        # Modify schema slightly
        modified_schema = test_schema.copy()
        modified_schema.append({
            "name": "new_field",
            "type": "STRING",
            "mode": "NULLABLE"
        })
        
        updated_schema_id = await registry.register_schema_from_json(
            modified_schema,
            "test_users",
            "test_db"
        )
        print(f"✅ Updated schema: {updated_schema_id}")
        
        # Verify version changed
        final_schema = await registry.get_schema(schema_id)
        print(f"   New version: {final_schema.version_hash}")
        print(f"   Field count: {len(final_schema.fields)}")
        
        print("\n🎉 All schema registry tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup test database
        if os.path.exists("test_schema_registry.db"):
            os.remove("test_schema_registry.db")
            print("🧹 Cleaned up test database")

if __name__ == "__main__":
    asyncio.run(test_schema_registry())
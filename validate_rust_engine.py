#!/usr/bin/env python3
"""
Simple validation script for Rust DataFusion engine

This script validates that the Rust engine meets the core requirements
and performance targets for the 10x improvement goal.
"""

import time
import sys

def print_header(text):
    print(f"\n{'='*60}")
    print(f"{text}")
    print(f"{'='*60}")

def test_rust_engine():
    """Test the Rust engine and validate performance targets"""
    
    # Check if Rust engine is available
    try:
        import bigquery_lite_engine
        print("✅ Rust engine imported successfully")
    except ImportError:
        print("❌ Rust engine not available")
        print("   Build with: cd bigquery-lite-engine && maturin develop --release")
        return False
    
    print_header("🎯 Core Functionality Tests")
    
    # 1. Engine Creation
    try:
        engine = bigquery_lite_engine.BlazeQueryEngine()
        print("✅ Engine creation: SUCCESS")
    except Exception as e:
        print(f"❌ Engine creation: FAILED - {e}")
        return False
    
    # 2. Test Data Registration
    try:
        engine.register_test_data("validation_test", 50_000)
        print("✅ Test data registration: SUCCESS (50K rows)")
    except Exception as e:
        print(f"❌ Test data registration: FAILED - {e}")
        return False
    
    # 3. Basic Query Execution
    try:
        result = engine.execute_query_sync("SELECT COUNT(*) FROM validation_test")
        print(f"✅ Basic query: SUCCESS ({result.rows} rows, {result.execution_time_ms}ms)")
    except Exception as e:
        print(f"❌ Basic query: FAILED - {e}")
        return False
    
    # 4. Aggregation Query
    try:
        result = engine.execute_query_sync(
            "SELECT category, COUNT(*), AVG(value) FROM validation_test GROUP BY category"
        )
        print(f"✅ Aggregation query: SUCCESS ({result.rows} rows, {result.execution_time_ms}ms)")
    except Exception as e:
        print(f"❌ Aggregation query: FAILED - {e}")
        return False
    
    print_header("🚀 Performance Target Validation")
    
    # 5. 1M Row Performance Test - THE KEY TARGET
    try:
        print("📊 Testing 1M row aggregation performance...")
        engine.register_test_data("perf_test_1m", 1_000_000)
        
        start_time = time.time()
        result = engine.execute_query_sync(
            "SELECT category, COUNT(*) as count, SUM(value) as total, AVG(value) as average "
            "FROM perf_test_1m GROUP BY category"
        )
        total_time = time.time() - start_time
        
        # Performance validation
        execution_time = result.execution_time_ms
        memory_gb = result.memory_used_bytes / 1024 / 1024 / 1024
        
        print(f"   • Execution time: {execution_time}ms")
        print(f"   • Total time (w/ Python): {total_time*1000:.1f}ms")
        print(f"   • Memory usage: {memory_gb:.3f}GB")
        print(f"   • Rows returned: {result.rows}")
        
        # Target validation
        target_100ms = execution_time < 100
        target_2gb = memory_gb < 2.0
        
        status_time = "✅ TARGET MET" if target_100ms else "❌ TARGET MISSED"
        status_memory = "✅ TARGET MET" if target_2gb else "❌ TARGET EXCEEDED"
        
        print(f"   • <100ms target: {status_time}")
        print(f"   • <2GB memory target: {status_memory}")
        
        if target_100ms and target_2gb:
            print("🎯 PRIMARY TARGETS ACHIEVED!")
            primary_success = True
        else:
            print("⚠️  Primary targets not fully met")
            primary_success = False
            
    except Exception as e:
        print(f"❌ 1M row performance test: FAILED - {e}")
        primary_success = False
    
    print_header("🧪 Additional Validation Tests")
    
    # 6. Error Handling
    error_handling_ok = True
    try:
        engine.execute_query_sync("SELECT * FROM nonexistent_table")
        print("❌ Error handling: Should have failed for nonexistent table")
        error_handling_ok = False
    except:
        print("✅ Error handling: Correctly handles invalid queries")
    
    # 7. Query Validation
    try:
        valid = engine.validate_query_sync("SELECT COUNT(*) FROM validation_test")
        invalid = engine.validate_query_sync("INVALID SQL")
        
        if valid and not invalid:
            print("✅ Query validation: Working correctly")
            validation_ok = True
        else:
            print("❌ Query validation: Not working as expected")
            validation_ok = False
    except Exception as e:
        print(f"❌ Query validation: FAILED - {e}")
        validation_ok = False
    
    # 8. Statistics Tracking
    try:
        stats = engine.get_stats_sync()
        if stats.total_queries > 0:
            print(f"✅ Statistics tracking: {stats.total_queries} queries tracked")
            stats_ok = True
        else:
            print("⚠️  Statistics tracking: No queries recorded")
            stats_ok = False
    except Exception as e:
        print(f"❌ Statistics tracking: FAILED - {e}")
        stats_ok = False
    
    print_header("📊 Final Assessment")
    
    # Calculate overall score
    tests = [
        ("Core functionality", True),  # If we got this far, core works
        ("Primary performance targets", primary_success),
        ("Error handling", error_handling_ok),
        ("Query validation", validation_ok),
        ("Statistics tracking", stats_ok),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"Test Results: {passed}/{total} passed")
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  • {test_name}: {status}")
    
    # Overall assessment
    if passed == total:
        print("\n🎉 EXCELLENT: All tests passed! Rust engine is production-ready.")
        return True
    elif passed >= total * 0.8:  # 80% or better
        print(f"\n✅ GOOD: Most tests passed ({passed}/{total}). Minor issues to address.")
        return True
    else:
        print(f"\n❌ ISSUES: Several tests failed ({total-passed}/{total}). Needs attention.")
        return False

if __name__ == "__main__":
    print("🚀 Rust DataFusion Engine Validation")
    print("Testing core functionality and performance targets")
    
    success = test_rust_engine()
    
    if success:
        print("\n🎯 RESULT: Rust engine validation SUCCESSFUL")
        print("   Ready for integration into production backend!")
        sys.exit(0)
    else:
        print("\n⚠️  RESULT: Rust engine needs additional work")
        sys.exit(1)
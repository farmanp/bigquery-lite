#!/usr/bin/env python3
"""
Comprehensive test runner for BigQuery-Lite with Rust engine

This script runs all test suites:
- Rust unit tests
- Python integration tests
- Performance benchmarks
- Memory validation
- Error handling tests
"""

import sys
import subprocess
import os
import time
from pathlib import Path

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")

def run_command(cmd, cwd=None, description=""):
    """Run a command and return success status"""
    try:
        print_info(f"Running: {' '.join(cmd)}" + (f" ({description})" if description else ""))
        start_time = time.time()
        
        result = subprocess.run(
            cmd, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        elapsed = time.time() - start_time
        print_success(f"Completed in {elapsed:.2f}s")
        
        # Show output if not empty
        if result.stdout.strip():
            print(f"{Colors.OKCYAN}Output:{Colors.ENDC}")
            print(result.stdout)
        
        return True, result.stdout
        
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print_error(f"Failed after {elapsed:.2f}s")
        print(f"{Colors.FAIL}Error output:{Colors.ENDC}")
        print(e.stderr)
        return False, e.stderr
    except FileNotFoundError:
        print_error(f"Command not found: {cmd[0]}")
        return False, "Command not found"

def check_rust_engine_available():
    """Check if Rust engine is built and available"""
    try:
        import bigquery_lite_engine
        return True
    except ImportError:
        return False

def main():
    """Main test runner"""
    print_header("🚀 BigQuery-Lite Comprehensive Test Suite")
    
    project_root = Path(__file__).parent
    rust_dir = project_root / "bigquery-lite-engine"
    backend_dir = project_root / "backend"
    
    # Test results tracking
    test_results = {
        "rust_unit_tests": False,
        "rust_build": False,
        "python_integration": False,
        "performance_benchmarks": False,
        "memory_validation": False,
        "error_handling": False,
    }
    
    # 1. Rust Unit Tests
    print_header("🦀 Rust Unit Tests")
    if rust_dir.exists():
        success, _ = run_command(
            ["cargo", "test", "--lib"], 
            cwd=rust_dir,
            description="Rust unit tests"
        )
        test_results["rust_unit_tests"] = success
    else:
        print_error("Rust directory not found")
    
    # 2. Build Rust Engine
    print_header("🔨 Building Rust Engine")
    if rust_dir.exists():
        # First check if maturin is available
        maturin_check, _ = run_command(["maturin", "--version"], description="Check maturin")
        
        if maturin_check:
            success, _ = run_command(
                ["maturin", "develop", "--release"], 
                cwd=rust_dir,
                description="Build Python extension"
            )
            test_results["rust_build"] = success
        else:
            print_warning("maturin not available - attempting pip install")
            pip_success, _ = run_command(["pip", "install", "maturin"])
            if pip_success:
                success, _ = run_command(
                    ["maturin", "develop", "--release"], 
                    cwd=rust_dir,
                    description="Build Python extension after installing maturin"
                )
                test_results["rust_build"] = success
            else:
                print_error("Failed to install maturin")
    else:
        print_error("Rust directory not found")
    
    # Check if Rust engine is now available
    rust_available = check_rust_engine_available()
    if rust_available:
        print_success("Rust engine is available for testing")
    else:
        print_warning("Rust engine not available - some tests will be skipped")
    
    # 3. Python Integration Tests
    print_header("🐍 Python Integration Tests")
    if backend_dir.exists():
        success, _ = run_command(
            ["python", "-m", "pytest", "tests/test_rust_integration.py", "-v"],
            cwd=backend_dir,
            description="Python FFI integration tests"
        )
        test_results["python_integration"] = success
    else:
        print_error("Backend directory not found")
    
    # 4. Performance Benchmarks (only if Rust engine available)
    print_header("⚡ Performance Benchmarks")
    if backend_dir.exists() and rust_available:
        success, _ = run_command(
            ["python", "-m", "pytest", "tests/test_performance_benchmarks.py", "-v", "-s"],
            cwd=backend_dir,
            description="Performance regression tests"
        )
        test_results["performance_benchmarks"] = success
    else:
        if not rust_available:
            print_warning("Skipping performance tests - Rust engine not available")
        else:
            print_error("Backend directory not found")
    
    # 5. Memory Validation Tests
    print_header("🧠 Memory Validation Tests")
    if backend_dir.exists() and rust_available:
        success, _ = run_command(
            ["python", "-m", "pytest", "tests/test_memory_validation.py", "-v"],
            cwd=backend_dir,
            description="Memory usage validation tests"
        )
        test_results["memory_validation"] = success
    else:
        if not rust_available:
            print_warning("Skipping memory tests - Rust engine not available")
        else:
            print_error("Backend directory not found")
    
    # 6. Error Handling Tests
    print_header("🛡️ Error Handling Tests")
    if backend_dir.exists() and rust_available:
        success, _ = run_command(
            ["python", "-m", "pytest", "tests/test_error_handling.py", "-v"],
            cwd=backend_dir,
            description="Error handling and edge case tests"
        )
        test_results["error_handling"] = success
    else:
        if not rust_available:
            print_warning("Skipping error handling tests - Rust engine not available")
        else:
            print_error("Backend directory not found")
    
    # 7. Optional: Run original benchmark
    print_header("📊 Original Benchmark (Optional)")
    if backend_dir.exists() and rust_available:
        print_info("Running original benchmark for comparison...")
        success, output = run_command(
            ["python", "test_rust_engine.py"],
            cwd=backend_dir,
            description="Original performance benchmark"
        )
        if success:
            print_success("Original benchmark completed")
        else:
            print_warning("Original benchmark had issues (non-critical)")
    
    # Summary
    print_header("📋 Test Results Summary")
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n{Colors.BOLD}Overall Results: {passed_tests}/{total_tests} tests passed{Colors.ENDC}")
    
    if passed_tests == total_tests:
        print_success("🎉 All tests passed! The Rust engine is ready for production.")
        return 0
    elif passed_tests >= total_tests * 0.8:  # 80% pass rate
        print_warning(f"⚠️  Most tests passed ({passed_tests}/{total_tests}). Review failures above.")
        return 1
    else:
        print_error(f"💥 Many tests failed ({total_tests - passed_tests}/{total_tests}). Significant issues detected.")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
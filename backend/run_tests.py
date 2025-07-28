#!/usr/bin/env python3
"""
Test runner script for BigQuery-Lite backend tests

This script provides convenient commands for running different types of tests:
- Unit tests only
- Integration tests only  
- All tests
- Tests with coverage reporting
- Tests with specific markers

Usage:
    python run_tests.py unit                    # Run unit tests only
    python run_tests.py integration             # Run integration tests only
    python run_tests.py all                     # Run all tests
    python run_tests.py coverage                # Run with coverage
    python run_tests.py --marker slow           # Run tests marked as slow
    python run_tests.py --help                  # Show help
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the exit code"""
    if description:
        print(f"\n🚀 {description}")
    
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def install_test_dependencies():
    """Install test dependencies"""
    return run_command([
        sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"
    ], "Installing test dependencies")


def run_unit_tests():
    """Run unit tests only"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "tests/unit/",
        "-v",
        "-m", "unit"
    ], "Running unit tests")


def run_integration_tests():
    """Run integration tests only"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "tests/integration/",
        "-v", 
        "-m", "integration"
    ], "Running integration tests")


def run_all_tests():
    """Run all tests"""
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v"
    ], "Running all tests")


def run_tests_with_coverage():
    """Run tests with coverage reporting"""
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--cov=runners",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov"
    ], "Running tests with coverage")


def run_tests_with_marker(marker):
    """Run tests with specific marker"""
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "-m", marker
    ], f"Running tests marked as '{marker}'")


def run_fast_tests():
    """Run fast tests only (exclude slow tests)"""
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "-m", "not slow"
    ], "Running fast tests only")


def run_duckdb_tests():
    """Run DuckDB tests only"""
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "-m", "requires_duckdb",
        "-k", "duckdb"
    ], "Running DuckDB tests only")


def run_clickhouse_tests():
    """Run ClickHouse tests only"""
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "-m", "requires_clickhouse",
        "-k", "clickhouse"
    ], "Running ClickHouse tests only")


def check_environment():
    """Check if test environment is properly set up"""
    print("🔍 Checking test environment...")
    
    # Check if pytest is installed
    try:
        import pytest
        print(f"✅ pytest {pytest.__version__} is installed")
    except ImportError:
        print("❌ pytest is not installed")
        return False
    
    # Check if test directories exist
    test_dirs = ["tests/", "tests/unit/", "tests/integration/", "tests/fixtures/"]
    for test_dir in test_dirs:
        if Path(test_dir).exists():
            print(f"✅ {test_dir} exists")
        else:
            print(f"❌ {test_dir} does not exist")
            return False
    
    # Check if runner modules can be imported
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from runners.duckdb_runner import DuckDBRunner
        from runners.clickhouse_runner import ClickHouseRunner
        print("✅ Runner modules can be imported")
    except ImportError as e:
        print(f"❌ Cannot import runner modules: {e}")
        return False
    
    print("✅ Test environment looks good!")
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test runner for BigQuery-Lite backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "command",
        choices=["unit", "integration", "all", "coverage", "fast", "duckdb", "clickhouse", "check", "install"],
        help="Test command to run"
    )
    
    parser.add_argument(
        "--marker", "-m",
        help="Run tests with specific pytest marker"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Handle special commands first
    if args.command == "check":
        success = check_environment()
        sys.exit(0 if success else 1)
    
    if args.command == "install":
        exit_code = install_test_dependencies()
        sys.exit(exit_code)
    
    # Check environment before running tests
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above.")
        sys.exit(1)
    
    # Run the requested tests
    exit_code = 0
    
    if args.marker:
        exit_code = run_tests_with_marker(args.marker)
    elif args.command == "unit":
        exit_code = run_unit_tests()
    elif args.command == "integration":
        exit_code = run_integration_tests()
    elif args.command == "all":
        exit_code = run_all_tests()
    elif args.command == "coverage":
        exit_code = run_tests_with_coverage()
    elif args.command == "fast":
        exit_code = run_fast_tests()
    elif args.command == "duckdb":
        exit_code = run_duckdb_tests()
    elif args.command == "clickhouse":
        exit_code = run_clickhouse_tests()
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
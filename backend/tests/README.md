# BigQuery-Lite Backend Test Suite

This directory contains comprehensive tests for the BigQuery-Lite backend, focusing on the database runners (DuckDB and ClickHouse).

## Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── fixtures/
│   └── sample_data.py       # Test data generators and mock responses
├── unit/
│   ├── test_duckdb_runner.py     # Unit tests for DuckDB runner
│   └── test_clickhouse_runner.py # Unit tests for ClickHouse runner
├── integration/
│   └── test_runners_integration.py # Integration tests with real databases
└── README.md               # This file
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Fast**: Run without external dependencies
- **Isolated**: Use mocks and fixtures instead of real databases
- **Comprehensive**: Test all methods, error conditions, and edge cases
- **Coverage**: Aim for >90% code coverage

**What they test:**
- Runner initialization and configuration
- SQL query parsing and validation
- Error handling and recovery
- Performance metrics calculation
- Data type conversion
- Query type detection and table extraction

### Integration Tests (`tests/integration/`)
- **Real databases**: Test with actual DuckDB and ClickHouse connections
- **End-to-end**: Test complete workflows
- **Performance**: Verify actual query execution and metrics
- **Compatibility**: Ensure both runners work with real data

**What they test:**
- Database connection and initialization
- Real SQL query execution
- Actual performance metrics collection
- Schema operations and table management
- Data ingestion and retrieval workflows
- Cross-runner compatibility

## Test Markers

Use pytest markers to categorize and selectively run tests:

- `@pytest.mark.unit` - Unit tests (fast, no external deps)
- `@pytest.mark.integration` - Integration tests (require databases)
- `@pytest.mark.slow` - Slow tests (may take several seconds)
- `@pytest.mark.requires_duckdb` - Tests requiring DuckDB
- `@pytest.mark.requires_clickhouse` - Tests requiring ClickHouse

## Running Tests

### Prerequisites

1. Install test dependencies:
   ```bash
   cd backend
   pip install -r requirements-test.txt
   ```

2. For integration tests, ensure databases are available:
   - **DuckDB**: Automatically available (embedded)
   - **ClickHouse**: Optional, tests will skip if not available

### Quick Start

```bash
# Run all tests
python run_tests.py all

# Run only unit tests (fast)
python run_tests.py unit

# Run with coverage report
python run_tests.py coverage

# Run specific database tests
python run_tests.py duckdb
python run_tests.py clickhouse
```

### Detailed Test Commands

```bash
# Check test environment
python run_tests.py check

# Install test dependencies
python run_tests.py install

# Run unit tests only
python run_tests.py unit

# Run integration tests only
python run_tests.py integration

# Run all tests
python run_tests.py all

# Run with coverage reporting
python run_tests.py coverage

# Run fast tests (exclude slow ones)
python run_tests.py fast

# Run tests with specific marker
python run_tests.py --marker slow
python run_tests.py --marker requires_clickhouse
```

### Using pytest directly

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_duckdb_runner.py -v

# Run tests matching pattern
pytest tests/ -k "test_execute_query" -v

# Run with coverage
pytest tests/ --cov=runners --cov-report=html

# Run only unit tests
pytest tests/ -m unit

# Run excluding slow tests
pytest tests/ -m "not slow"

# Run with parallel execution
pytest tests/ -n auto
```

## Test Configuration

Configuration is handled in:
- **pytest.ini**: Main pytest configuration
- **conftest.py**: Shared fixtures and test setup
- **requirements-test.txt**: Test dependencies

### Key Configuration Options

```ini
# pytest.ini
[tool:pytest]
testpaths = tests
addopts = 
    -v                          # Verbose output
    --strict-markers           # Require marker definitions
    --cov=runners              # Coverage for runners package
    --cov-fail-under=80        # Minimum 80% coverage
asyncio_mode = auto            # Auto-detect async tests
```

## Writing Tests

### Test Structure

Follow this pattern for test classes:

```python
class TestDuckDBRunner:
    """Test cases for DuckDBRunner class"""

    @pytest.fixture
    def runner(self, temp_db_path):
        """Create a DuckDBRunner instance for testing"""
        return DuckDBRunner(db_path=temp_db_path)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_method_name(self, runner, other_fixtures):
        """Test description"""
        # Arrange
        # Act  
        # Assert
```

### Best Practices

1. **Use descriptive test names**: `test_execute_query_with_invalid_sql`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Test edge cases**: Empty inputs, errors, boundary conditions
4. **Use appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.integration`
5. **Mock external dependencies** in unit tests
6. **Use real databases** in integration tests
7. **Clean up resources**: Use fixtures with proper teardown

### Fixtures

Common fixtures available:

```python
# Database fixtures
temp_db_path                  # Temporary database file path
mock_clickhouse_client        # Mock ClickHouse client
mock_duckdb_connection        # Mock DuckDB connection

# Data fixtures  
sample_sql_queries           # Various SQL query samples
sample_query_results         # Expected query results
performance_metrics_sample   # Sample performance metrics

# Environment fixtures
clickhouse_env_vars          # ClickHouse environment variables
```

## Coverage Reports

Coverage reports are generated in multiple formats:

1. **Terminal**: Shows missing lines during test run
2. **HTML**: Detailed report in `htmlcov/` directory
3. **Fail threshold**: Tests fail if coverage drops below 80%

View HTML coverage report:
```bash
python run_tests.py coverage
open htmlcov/index.html  # macOS
# or 
firefox htmlcov/index.html  # Linux
```

## Continuous Integration

Tests are designed to run in CI environments:

- **No external dependencies** for unit tests
- **Graceful degradation** when databases unavailable
- **Proper test isolation** and cleanup
- **Deterministic results** with seeded random data

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: |
          cd backend
          python run_tests.py coverage
```

## Database-Specific Testing

### DuckDB Tests

- **Always available**: DuckDB is embedded, no setup required
- **File-based**: Uses temporary files for isolation
- **Fast**: In-memory or temporary file operations

### ClickHouse Tests

- **Optional**: Tests skip if ClickHouse not available
- **Connection testing**: Graceful handling of connection failures
- **Environment variables**: Uses `CLICKHOUSE_*` env vars for configuration

### Setting up ClickHouse for Testing

```bash
# Using Docker
docker run -d --name clickhouse-test \
  -p 8123:8123 -p 9000:9000 \
  -e CLICKHOUSE_USER=admin \
  -e CLICKHOUSE_PASSWORD=password \
  clickhouse/clickhouse-server

# Environment variables for tests
export CLICKHOUSE_HOST=localhost
export CLICKHOUSE_PORT=8123
export CLICKHOUSE_USER=admin
export CLICKHOUSE_PASSWORD=password
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're in the backend directory
2. **Database connection failures**: Check environment variables
3. **Test isolation**: Use fixtures for proper setup/teardown
4. **Async test issues**: Use `@pytest.mark.asyncio` decorator

### Debug Mode

Run tests with extra debugging:

```bash
# Verbose output with stdout
pytest tests/ -v -s

# Debug specific test
pytest tests/unit/test_duckdb_runner.py::TestDuckDBRunner::test_method -v -s

# Drop into debugger on failure
pytest tests/ --pdb
```

### Performance Issues

If tests are slow:

1. Run only fast tests: `python run_tests.py fast`
2. Use parallel execution: `pytest tests/ -n auto`
3. Profile slow tests: `pytest tests/ --durations=10`

## Contributing

When adding new tests:

1. **Write unit tests** for all new functionality
2. **Add integration tests** for database interactions
3. **Update fixtures** if adding new test data
4. **Maintain coverage** above 80%
5. **Add appropriate markers** for test categorization
6. **Update this README** if adding new test patterns

## Test Data

Test data is generated dynamically using the `SampleDataGenerator` class:

- **NYC Taxi Data**: Realistic taxi trip records
- **User Events**: Web analytics event data  
- **Performance Metrics**: Simulated performance data

This ensures:
- **No large test files** in the repository
- **Flexible data generation** for different test scenarios
- **Reproducible tests** with consistent data patterns
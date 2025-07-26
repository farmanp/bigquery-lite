# Development Guide

This guide helps you set up a development environment for BigQuery-Lite and understand the project structure for contributing.

## Development Environment Setup

### Prerequisites

- **Python 3.8+** (3.11+ recommended)
- **Node.js 16+** and **npm**
- **Git** for version control
- **Docker** (optional, for ClickHouse)

### Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/farmanp/bigquery-lite.git
cd bigquery-lite

# 2. Set up backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Set up frontend
cd ../frontend
npm install

# 4. Install CLI tool
cd ..
pip install -e .
```

## Project Structure

```
bigquery-lite/
├── docs/                    # Documentation
├── backend/                 # FastAPI backend
│   ├── app.py              # Main application
│   ├── runners/            # Database engine runners
│   │   ├── duckdb_runner.py
│   │   └── clickhouse_runner.py
│   ├── schema_registry.py  # Schema management
│   ├── schema_translator.py # Schema translation
│   ├── protobuf_ingester.py # Data ingestion
│   └── requirements.txt    # Python dependencies
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── App.js         # Main app component
│   │   └── index.js       # Entry point
│   └── package.json       # Node.js dependencies
├── bqlite/                # CLI tool
│   └── cli.py            # Command-line interface
├── data/                  # Sample datasets
├── notebooks/             # Jupyter notebooks
├── screenshots/           # UI screenshots
├── docker-compose.yml     # Docker services
└── setup.py              # Package configuration
```

## Development Workflow

### 1. Backend Development

#### Start Backend Server

```bash
cd backend
source venv/bin/activate
python app.py
```

The backend will be available at http://localhost:8001

#### Backend Development Tips

- **Auto-reload**: The server automatically reloads on code changes
- **API Docs**: Visit http://localhost:8001/docs for interactive documentation
- **Health Check**: Test with `curl http://localhost:8001/health`

#### Key Backend Components

**FastAPI Application (`app.py`)**
- Main application entry point
- API route definitions
- Request/response models
- Error handling

**Database Runners (`runners/`)**
- `duckdb_runner.py` - Embedded DuckDB operations
- `clickhouse_runner.py` - ClickHouse cluster operations
- Abstract base class for consistent interface

**Schema Management**
- `schema_registry.py` - Schema storage and versioning
- `schema_translator.py` - BigQuery to SQL DDL translation
- `protobuf_ingester.py` - Binary data processing

### 2. Frontend Development

#### Start Frontend Server

```bash
cd frontend
npm start
```

The frontend will be available at http://localhost:3000

#### Frontend Development Tips

- **Hot Reload**: Changes automatically refresh in browser
- **Proxy Configuration**: API calls proxy to backend at localhost:8001
- **Component Development**: Use React DevTools for debugging

#### Key Frontend Components

**Main Application (`src/App.js`)**
- Application state management
- API communication
- Route handling

**UI Components (`src/components/`)**
- `SQLEditor.js` - Monaco editor integration
- `ResultsPanel.js` - Query results display
- `SchemaBrowser.js` - Schema exploration
- `QueryTabs.js` - Tab management

### 3. CLI Development

#### Test CLI Tool

```bash
# Install in development mode
pip install -e .

# Test commands
bqlite --help
bqlite list-schemas
```

#### CLI Development Tips

- **Live Updates**: Changes are immediately available after installation
- **Rich Output**: Uses Rich library for formatted output
- **Error Handling**: Comprehensive error messages and help

## Testing

### Backend Testing

```bash
cd backend

# Run basic tests
python -m pytest

# Test specific functionality
python test_schema_registry.py
python test_protobuf_ingestion.py

# Test API endpoints
curl -X POST "http://localhost:8001/queries" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT 1", "engine": "duckdb"}'
```

### Frontend Testing

```bash
cd frontend

# Run tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage
```

### Integration Testing

```bash
# Test complete workflow
bqlite register backend/test_data/user_events.proto --table test_events
bqlite create-table test_events --engines duckdb
bqlite ingest backend/test_data/sample_events.pb --schema test_events
```

## Database Development

### DuckDB Development

DuckDB runs embedded in the backend process:

```python
# Example DuckDB operations
from runners.duckdb_runner import DuckDBRunner

runner = DuckDBRunner()
result = runner.execute_query("SELECT COUNT(*) FROM nyc_taxi")
```

### ClickHouse Development

#### Start ClickHouse with Docker

```bash
# Start ClickHouse cluster
docker-compose up clickhouse-server clickhouse-worker1 clickhouse-worker2

# Test ClickHouse connection
curl http://localhost:8123/ping
```

#### ClickHouse Development Tips

- **HTTP Interface**: Use port 8123 for HTTP queries
- **Native Interface**: Use port 9000 for native client
- **Cluster Configuration**: Multi-node setup for testing distributed queries

## Code Standards

### Python Code Style

```python
# Use type hints
def process_query(sql: str, engine: str) -> Dict[str, Any]:
    pass

# Use async/await for I/O operations
async def execute_query(query: QueryRequest) -> QueryResult:
    pass

# Use descriptive variable names
query_execution_time = time.time() - start_time

# Use docstrings for functions and classes
def translate_schema(schema: dict) -> str:
    """
    Translate BigQuery schema to SQL DDL.
    
    Args:
        schema: BigQuery schema dictionary
        
    Returns:
        SQL DDL string
    """
    pass
```

### JavaScript/React Code Style

```javascript
// Use functional components with hooks
const SQLEditor = ({ value, onChange, onExecute }) => {
  const [isLoading, setIsLoading] = useState(false);
  
  return (
    <div className="sql-editor">
      {/* Component JSX */}
    </div>
  );
};

// Use descriptive variable names
const queryExecutionTime = performance.now() - startTime;

// Use proper error handling
try {
  const response = await executeQuery(queryText);
  setResults(response.data);
} catch (error) {
  setError(error.message);
}
```

### Documentation Standards

- **Comments**: Use clear, descriptive comments
- **Docstrings**: Document all public functions and classes
- **README**: Update documentation for new features
- **API Docs**: FastAPI automatically generates API documentation

## Debugging

### Backend Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use pdb for debugging
import pdb; pdb.set_trace()

# Check database connections
from runners.clickhouse_runner import ClickHouseRunner
runner = ClickHouseRunner()
runner.test_connection()
```

### Frontend Debugging

```javascript
// Use browser DevTools
console.log('Query response:', response);

// React DevTools for component inspection
// Browser Network tab for API call debugging

// Error boundaries for error handling
const ErrorBoundary = ({ children }) => {
  // Error boundary implementation
};
```

### Common Debugging Scenarios

**Backend Issues:**
- Check backend logs: `python app.py` output
- Test API directly: `curl http://localhost:8001/health`
- Verify database connections
- Check environment variables

**Frontend Issues:**
- Check browser console for errors
- Verify backend connectivity
- Test API calls in browser Network tab
- Check React component state

**Database Issues:**
- Test ClickHouse: `curl http://localhost:8123/ping`
- Check DuckDB files in backend directory
- Verify data files exist in `data/` directory

## Performance Optimization

### Backend Performance

```python
# Use async operations
async def execute_query(query: str) -> dict:
    # Async database operations
    pass

# Cache frequently used data
from functools import lru_cache

@lru_cache(maxsize=100)
def get_schema_translation(schema_hash: str) -> str:
    # Cached schema translation
    pass

# Use connection pooling for databases
# Implement query result caching
```

### Frontend Performance

```javascript
// Use React.memo for expensive components
const ResultsTable = React.memo(({ data }) => {
  // Component implementation
});

// Use useMemo for expensive calculations
const processedData = useMemo(() => {
  return data.map(row => processRow(row));
}, [data]);

// Use useCallback for event handlers
const handleExecute = useCallback(() => {
  // Event handler
}, [queryText]);
```

## Adding New Features

### Backend Feature Development

1. **Create API Endpoint**
   ```python
   @app.post("/new-feature")
   async def new_feature(request: NewFeatureRequest):
       # Implementation
       pass
   ```

2. **Add Request/Response Models**
   ```python
   class NewFeatureRequest(BaseModel):
       parameter: str
       
   class NewFeatureResponse(BaseModel):
       result: str
   ```

3. **Implement Business Logic**
   ```python
   class NewFeatureService:
       def process(self, request: NewFeatureRequest) -> NewFeatureResponse:
           # Business logic
           pass
   ```

4. **Add Tests**
   ```python
   def test_new_feature():
       # Test implementation
       pass
   ```

### Frontend Feature Development

1. **Create React Component**
   ```javascript
   const NewFeatureComponent = () => {
     // Component implementation
   };
   ```

2. **Add API Integration**
   ```javascript
   const useNewFeature = () => {
     const [result, setResult] = useState(null);
     
     const callNewFeature = async (params) => {
       const response = await axios.post('/new-feature', params);
       setResult(response.data);
     };
     
     return { result, callNewFeature };
   };
   ```

3. **Integrate with Main App**
   ```javascript
   // Add to App.js or appropriate parent component
   ```

### CLI Feature Development

1. **Add Command**
   ```python
   @app.command("new-feature")
   def new_feature(param: str = typer.Argument(...)):
       """New feature description."""
       # Implementation
       pass
   ```

2. **Add API Integration**
   ```python
   def call_backend_api(param: str) -> dict:
       # HTTP client call
       pass
   ```

## Contributing Workflow

### 1. Prepare Changes

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# ... development work ...

# Test changes
# ... run tests ...
```

### 2. Code Quality

```bash
# Format Python code
black backend/
isort backend/

# Format JavaScript code
cd frontend
npm run format

# Run linting
npm run lint
```

### 3. Commit and Push

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add new feature for X functionality"

# Push to remote
git push origin feature/new-feature
```

### 4. Pull Request

1. Create pull request on GitHub
2. Describe changes and testing performed
3. Link related issues
4. Request review from maintainers

## Development Tips

### Efficient Development

1. **Use Multiple Terminals**
   - Terminal 1: Backend development
   - Terminal 2: Frontend development
   - Terminal 3: CLI testing
   - Terminal 4: Database operations

2. **Hot Reload**
   - Backend auto-reloads on changes
   - Frontend hot-reloads in browser
   - CLI updates immediately after `pip install -e .`

3. **API Testing**
   - Use FastAPI docs at http://localhost:8001/docs
   - Use curl or Postman for testing
   - Monitor network requests in browser

4. **Database Development**
   - Use ClickHouse client for direct queries
   - DuckDB CLI for debugging embedded operations
   - Monitor query execution in backend logs

### Troubleshooting Development Issues

**Python Import Errors:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install in development mode
pip install -e .
```

**Node.js Module Errors:**
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Database Connection Issues:**
```bash
# Check ClickHouse status
docker-compose ps
curl http://localhost:8123/ping

# Check backend health
curl http://localhost:8001/health
```

## Next Steps

- **[Code Standards](code-standards.md)** - Detailed coding conventions
- **[Testing Guide](testing.md)** - Comprehensive testing strategies
- **[Contributing Guidelines](contributing.md)** - How to contribute to the project
- **[API Reference](../api/rest-api.md)** - Backend API documentation
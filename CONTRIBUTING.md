# Contributing to BigQuery-Lite

Thank you for your interest in contributing to BigQuery-Lite! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)
- [Community](#community)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.8+** installed
- **Node.js 16+** and npm
- **Docker** and Docker Compose
- **Git** for version control
- Basic knowledge of SQL, Python, and React

### Quick Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/bigquery-lite.git
   cd bigquery-lite
   ```

2. **Set Up Development Environment**
   ```bash
   # Backend setup
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   
   pip install -r backend/requirements.txt
   pip install -r requirements-cli.txt
   
   # Frontend setup
   cd frontend
   npm install
   cd ..
   ```

3. **Start Development Services**
   ```bash
   # Terminal 1: Backend
   cd backend && python app.py
   
   # Terminal 2: Frontend
   cd frontend && npm start
   
   # Terminal 3: ClickHouse (optional)
   docker-compose up clickhouse-server
   ```

4. **Verify Setup**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8001
   - API Docs: http://localhost:8001/docs

## Development Setup

### Full Docker Development

For a complete development environment:

```bash
# Start all services
docker-compose up --build

# Or start specific services
docker-compose up frontend backend clickhouse-server
```

### IDE Configuration

#### VS Code (Recommended)

Install recommended extensions:
- Python (Microsoft)
- ES7+ React/Redux/React-Native snippets
- Docker
- SQL Highlight

#### Settings
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "editor.formatOnSave": true,
    "python.formatting.provider": "black"
}
```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

1. **Bug Fixes**: Fix issues and improve stability
2. **Feature Development**: Add new functionality
3. **Documentation**: Improve or add documentation
4. **Testing**: Add or improve test coverage
5. **Performance**: Optimize query execution or UI performance
6. **UX/UI**: Enhance user experience and interface design

### Contribution Workflow

1. **Check Existing Issues**: Look for existing issues or create a new one
2. **Discuss First**: For major changes, discuss in an issue first
3. **Fork & Branch**: Create a feature branch from `main`
4. **Develop**: Make your changes following our guidelines
5. **Test**: Ensure all tests pass and add new tests if needed
6. **Document**: Update documentation as necessary
7. **Submit PR**: Create a pull request with clear description

### Finding Ways to Contribute

- Check [Issues](https://github.com/farmanp/bigquery-lite/issues) labeled with `good first issue`
- Look for `help wanted` labels
- Review [Architecture Decision Records](adr/README.md) for context
- Check the [roadmap](docs/DESIGN.md#future-enhancements) for planned features

## Pull Request Process

### Before Submitting

1. **Update Documentation**: Ensure relevant docs are updated
2. **Add Tests**: Include tests for new functionality
3. **Run Tests**: Verify all tests pass locally
4. **Code Quality**: Follow coding standards and run linters
5. **Commit Messages**: Use clear, descriptive commit messages

### PR Requirements

- **Clear Title**: Descriptive title summarizing the change
- **Detailed Description**: Explain what changes were made and why
- **Issue Reference**: Link to related issues if applicable
- **Screenshots**: Include UI changes screenshots if relevant
- **Breaking Changes**: Clearly document any breaking changes

### PR Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Existing tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Screenshots (if applicable)
[Add screenshots here]

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have performed a self-review of my code
- [ ] I have commented my code where necessary
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
```

## Coding Standards

### Python (Backend)

#### Style Guide
- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Maximum line length: 88 characters

#### Code Quality Tools
```bash
# Format code
black backend/
isort backend/

# Lint code
flake8 backend/
pylint backend/

# Type checking
mypy backend/
```

#### Best Practices
- Use type hints for function parameters and return values
- Write docstrings for classes and functions
- Use async/await for I/O operations
- Handle exceptions appropriately
- Use meaningful variable and function names

#### Example Code Style
```python
from typing import List, Optional
import asyncio

async def execute_query(
    sql: str, 
    engine: str = "duckdb",
    timeout: int = 300
) -> Optional[QueryResult]:
    """
    Execute a SQL query using the specified engine.
    
    Args:
        sql: The SQL query to execute
        engine: Database engine to use ('duckdb' or 'clickhouse')
        timeout: Query timeout in seconds
        
    Returns:
        Query result or None if execution failed
        
    Raises:
        QueryTimeoutError: If query exceeds timeout
        QueryExecutionError: If query execution fails
    """
    try:
        # Implementation here
        pass
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise QueryExecutionError(str(e))
```

### JavaScript/React (Frontend)

#### Style Guide
- Use [ESLint](https://eslint.org/) and [Prettier](https://prettier.io/)
- Use functional components with hooks
- Use TypeScript for type safety (where applicable)
- Follow React best practices

#### Code Quality Tools
```bash
# Lint and format
npm run lint
npm run format

# Type checking (if using TypeScript)
npm run type-check
```

#### Best Practices
- Use descriptive component and variable names
- Keep components small and focused
- Use React hooks properly
- Handle loading and error states
- Optimize performance with React.memo when needed

#### Example Component Style
```jsx
import React, { useState, useEffect } from 'react';
import { QueryResult } from '../types';

interface ResultsTableProps {
  data: QueryResult[];
  loading: boolean;
  onRowClick?: (row: QueryResult) => void;
}

const ResultsTable: React.FC<ResultsTableProps> = ({ 
  data, 
  loading, 
  onRowClick 
}) => {
  const [sortColumn, setSortColumn] = useState<string>('');
  
  useEffect(() => {
    // Effect logic here
  }, [data]);

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="results-table">
      {/* Component implementation */}
    </div>
  );
};

export default ResultsTable;
```

### SQL Standards

- Use UPPERCASE for SQL keywords
- Use snake_case for table and column names
- Include appropriate comments for complex queries
- Use proper indentation and formatting

```sql
-- Good example
SELECT 
    user_id,
    COUNT(*) as total_queries,
    AVG(execution_time_ms) as avg_execution_time
FROM query_history 
WHERE created_at >= '2024-01-01'
    AND status = 'completed'
GROUP BY user_id
ORDER BY total_queries DESC;
```

## Testing Guidelines

### Backend Testing

#### Test Structure
```
backend/tests/
├── unit/           # Unit tests for individual functions
├── integration/    # Integration tests for components
├── e2e/           # End-to-end API tests
└── fixtures/      # Test data and fixtures
```

#### Writing Tests
```python
import pytest
from backend.runners.duckdb_runner import DuckDBRunner

class TestDuckDBRunner:
    @pytest.fixture
    def runner(self):
        return DuckDBRunner()
    
    async def test_simple_query(self, runner):
        result = await runner.execute_query("SELECT 1 as test")
        assert result.status == "completed"
        assert result.data[0]["test"] == 1
    
    async def test_invalid_query(self, runner):
        with pytest.raises(QueryExecutionError):
            await runner.execute_query("INVALID SQL")
```

#### Running Tests
```bash
# Run all tests
pytest backend/tests/

# Run specific test file
pytest backend/tests/test_duckdb_runner.py

# Run with coverage
pytest --cov=backend backend/tests/
```

### Frontend Testing

#### Test Structure
```
frontend/src/
├── components/
│   ├── Component.js
│   └── Component.test.js
└── utils/
    ├── helper.js
    └── helper.test.js
```

#### Writing Tests
```jsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import SQLEditor from './SQLEditor';

describe('SQLEditor', () => {
  test('renders with default placeholder', () => {
    render(<SQLEditor />);
    expect(screen.getByPlaceholderText(/enter sql query/i)).toBeInTheDocument();
  });

  test('calls onQuerySubmit when executed', () => {
    const mockSubmit = jest.fn();
    render(<SQLEditor onQuerySubmit={mockSubmit} />);
    
    const executeButton = screen.getByText(/execute/i);
    fireEvent.click(executeButton);
    
    expect(mockSubmit).toHaveBeenCalled();
  });
});
```

#### Running Tests
```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage
```

## Documentation

### Types of Documentation

1. **README Files**: Overview and quick start guides
2. **API Documentation**: Endpoint specifications and examples
3. **Architecture Docs**: System design and technical decisions
4. **User Guides**: Step-by-step usage instructions
5. **Code Comments**: Inline documentation

### Documentation Standards

- Write clear, concise documentation
- Include code examples where appropriate
- Keep documentation up-to-date with code changes
- Use markdown formatting consistently
- Include screenshots for UI features

### Building Documentation

The project uses Docusaurus for comprehensive documentation:

```bash
cd website
npm install
npm start  # Development server
npm run build  # Production build
```

## Issue Reporting

### Before Creating an Issue

1. **Search Existing Issues**: Check if the issue already exists
2. **Check Documentation**: Review docs for solutions
3. **Reproduce the Issue**: Ensure you can consistently reproduce it
4. **Gather Information**: Collect relevant logs, screenshots, and system info

### Issue Template

```markdown
## Bug Report / Feature Request

### Description
Clear description of the issue or feature request.

### Steps to Reproduce (for bugs)
1. Step one
2. Step two
3. Step three

### Expected Behavior
What should happen?

### Actual Behavior
What actually happens?

### Environment
- OS: [e.g., Ubuntu 20.04, Windows 10]
- Python Version: [e.g., 3.9.7]
- Node Version: [e.g., 16.14.0]
- Docker Version: [e.g., 20.10.12]

### Additional Context
Any other relevant information, logs, or screenshots.
```

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community discussion
- **Pull Requests**: Code review and collaboration

### Getting Help

1. **Documentation**: Check the [docs](docs/README.md) first
2. **Issues**: Search existing issues for solutions
3. **Discussions**: Ask questions in GitHub Discussions
4. **Community**: Engage with other contributors

### Recognition

Contributors are recognized in:
- **CHANGELOG.md**: Major contributions listed in release notes
- **README.md**: Contributors section
- **GitHub**: Contributor graphs and statistics

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

### Release Workflow

1. **Feature Freeze**: No new features for release candidate
2. **Testing**: Comprehensive testing of release candidate
3. **Documentation**: Update CHANGELOG.md and documentation
4. **Tagging**: Create git tag with version number
5. **Release**: Publish release with release notes

---

Thank you for contributing to BigQuery-Lite! Your contributions help make this project better for everyone.
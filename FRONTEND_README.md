# BigQuery-Lite Frontend 🖥️

A React-based web interface that mimics the BigQuery console for local analytics using DuckDB and ClickHouse.

## 🎯 Features

- **BigQuery-like Interface**: Familiar UI design matching Google BigQuery console
- **Monaco SQL Editor**: Advanced SQL editor with syntax highlighting and autocomplete
- **Dual Engine Support**: Switch between DuckDB (interactive) and ClickHouse (distributed)
- **Real-time Results**: Live query execution with progress tracking
- **Query Plans**: Detailed execution plans and performance metrics
- **Job History**: Track and replay previous queries
- **Responsive Design**: Works on desktop and mobile devices

## 🏗️ Architecture

```
frontend/
├── public/                 # Static assets
│   ├── index.html         # Main HTML template
│   ├── manifest.json      # PWA manifest
│   └── favicon.ico        # Application icon
├── src/
│   ├── components/        # React components
│   │   ├── Header.js      # Top navigation bar
│   │   ├── Sidebar.js     # Left panel (datasets, samples, history)
│   │   ├── SQLEditor.js   # Monaco-based SQL editor
│   │   ├── ResultsPanel.js # Results and execution details
│   │   ├── ResultsTable.js # Data table component
│   │   └── QueryPlan.js   # Query plan visualization
│   ├── App.js             # Main application component
│   ├── App.css            # Application styles
│   ├── index.js           # React entry point
│   └── index.css          # Global styles
└── package.json           # Dependencies and scripts
```

## 🚀 Quick Start

### Prerequisites

- Node.js 16+ and npm
- Backend server running on port 8001

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The application will be available at `http://localhost:3000`

### Production Build

```bash
# Create production build
npm run build

# Serve static files (requires serve package)
npx serve -s build
```

## 🎮 Usage Guide

### 1. SQL Editor

The Monaco editor provides:
- **Syntax Highlighting**: SQL keywords, functions, and operators
- **Auto-completion**: Table names, column names, and SQL functions
- **Error Detection**: Basic SQL syntax validation
- **Keyboard Shortcuts**:
  - `Ctrl/Cmd + Enter`: Execute query
  - `Ctrl/Cmd + /`: Toggle line comment
  - `F1`: Open command palette

### 2. Engine Selection

Choose between two execution engines:

- **DuckDB**: Fast embedded analytics, great for exploratory analysis
- **ClickHouse**: Distributed OLAP, better for large-scale analytics

### 3. Query Execution

1. Write your SQL query in the editor
2. Select the engine (DuckDB or ClickHouse)
3. Click "Run Query" or press `Ctrl/Cmd + Enter`
4. Monitor execution progress in real-time
5. View results in the table below

### 4. Results View

The results panel shows:
- **Results Tab**: Query results in a sortable table
- **Execution Details Tab**: Query plan and performance metrics

### 5. Sample Queries

Use the sidebar to:
- Browse available datasets
- Load sample queries for testing
- View query history and re-run queries

## 🎨 Component Details

### Header Component

Displays:
- Application title and logo
- System status (available slots, running queries)
- Real-time execution indicators

```jsx
<Header 
  systemStatus={systemStatus}
  isExecuting={isExecuting}
/>
```

### SQL Editor Component

Monaco-based editor with SQL support:

```jsx
<SQLEditor
  value={queryText}
  onChange={setQueryText}
  onExecute={executeQuery}
  disabled={isExecuting}
/>
```

**Features:**
- SQL syntax highlighting
- Auto-completion for keywords
- Query execution shortcut
- Line numbers and code folding

### Results Panel Component

Displays query results and execution details:

```jsx
<ResultsPanel
  results={queryResults}
  queryPlan={queryPlan}
  error={queryError}
  isLoading={isExecuting}
  currentJob={currentJob}
  activeTab={activeTab}
  onTabChange={setActiveTab}
/>
```

### Sidebar Component

Navigation and tools:

```jsx
<Sidebar 
  jobHistory={jobHistory}
  onLoadQuery={loadSampleQuery}
  systemStatus={systemStatus}
/>
```

**Sections:**
- **Data**: Available datasets and tables
- **Samples**: Pre-built example queries
- **History**: Previous query executions

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
# Backend API URL
REACT_APP_API_BASE_URL=http://localhost:8001

# Enable development features
REACT_APP_DEBUG=true
```

### API Integration

The frontend communicates with the backend via REST API:

```javascript
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001';

// Submit query
const response = await axios.post(`${API_BASE_URL}/queries`, {
  sql: queryText,
  engine: selectedEngine,
  priority: 1,
  estimated_slots: 1
});

// Get results
const result = await axios.get(`${API_BASE_URL}/jobs/${jobId}/result`);
```

## 🎯 Key Features Implementation

### Real-time Query Execution

```javascript
// Poll for job updates
useEffect(() => {
  if (!currentJob || currentJob.status === 'completed') return;
  
  const pollJob = async () => {
    const response = await axios.get(`${API_BASE_URL}/jobs/${currentJob.job_id}`);
    setCurrentJob(response.data);
    
    if (response.data.status === 'completed') {
      // Fetch results
      const resultResponse = await axios.get(`${API_BASE_URL}/jobs/${currentJob.job_id}/result`);
      setQueryResults(resultResponse.data.result);
    }
  };
  
  const interval = setInterval(pollJob, 1000);
  return () => clearInterval(interval);
}, [currentJob]);
```

### Dynamic Table Rendering

```javascript
const ResultsTable = ({ results }) => {
  const { columns, rows } = useMemo(() => {
    if (!results?.data) return { columns: [], rows: [] };
    
    // Extract columns from first row
    const firstRow = results.data[0];
    const cols = Object.keys(firstRow).map(key => ({
      key,
      header: key,
      type: inferColumnType(results.data, key)
    }));
    
    return { columns: cols, rows: results.data };
  }, [results]);
  
  // Render table with proper formatting
};
```

### Query Plan Visualization

```javascript
const QueryPlan = ({ plan }) => {
  return (
    <div>
      {/* Execution Summary */}
      <div className="execution-summary">
        <div>Execution Time: {formatTime(plan.execution_time)}</div>
        <div>Memory Used: {formatMemory(plan.memory_used_mb)}</div>
        <div>Rows Processed: {formatNumber(plan.rows_processed)}</div>
      </div>
      
      {/* Detailed Plan */}
      <pre className="query-plan">
        {plan.query_plan}
      </pre>
    </div>
  );
};
```

## 🎨 Styling

The interface uses a BigQuery-inspired design:

- **Color Palette**: Google Material Design colors
- **Typography**: Google Sans font family
- **Icons**: Material Icons
- **Layout**: Flexbox-based responsive design

### Key Style Classes

```css
.bq-button {
  background: #4285f4;
  color: white;
  border-radius: 4px;
  padding: 10px 20px;
}

.bq-table {
  border-collapse: collapse;
  width: 100%;
}

.bq-table th {
  background: #f8f9fa;
  border-bottom: 2px solid #e8eaed;
}
```

## 🐛 Troubleshooting

### Common Issues

**1. Backend Connection Failed**
```
Error: Network Error
```
- Ensure backend is running on port 8001
- Check CORS configuration
- Verify API_BASE_URL environment variable

**2. Monaco Editor Not Loading**
```
Error: Failed to load Monaco Editor
```
- Clear browser cache
- Check console for JavaScript errors
- Ensure CDN resources are accessible

**3. Query Results Not Displaying**
```
Results show "No data to display"
```
- Check network tab for API errors
- Verify query syntax
- Ensure sample data is loaded in backend

### Performance Tips

1. **Large Result Sets**: Results are automatically limited to prevent browser freezing
2. **Memory Usage**: Clear query history periodically
3. **Network**: Use local backend for best performance

## 🔄 Development Workflow

### Adding New Features

1. **Create Component**: Add new component in `src/components/`
2. **Update State**: Modify App.js state management
3. **Style Component**: Add styles to match BigQuery design
4. **Test Integration**: Verify backend API integration

### Code Organization

- **Components**: Reusable UI components
- **Hooks**: Custom React hooks for state management
- **Utils**: Helper functions and formatters
- **API**: Backend integration utilities

## 📱 Mobile Support

The interface is responsive and works on mobile devices:

- **Collapsible Sidebar**: Sidebar becomes a bottom panel on mobile
- **Touch-friendly**: Larger touch targets for mobile interaction
- **Responsive Tables**: Horizontal scrolling for large result sets

## 🚀 Future Enhancements

- **Query Autocomplete**: Table and column name suggestions
- **Visual Query Builder**: Drag-and-drop query construction
- **Dashboard Creation**: Save and share query results
- **Export Options**: Download results as CSV, JSON, Excel
- **Collaboration**: Share queries with team members

---

The BigQuery-Lite frontend provides a familiar and powerful interface for local analytics, bringing the BigQuery experience to your local development environment! 🎉
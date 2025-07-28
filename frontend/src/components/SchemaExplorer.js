import React, { useState, useEffect, useCallback, useImperativeHandle, forwardRef } from 'react';
import axios from 'axios';

const SchemaExplorer = forwardRef(({ apiBaseUrl, systemStatus }, ref) => {
  const [schemas, setSchemas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedEngine, setSelectedEngine] = useState('duckdb');
  const [expandedDatasets, setExpandedDatasets] = useState(new Set(['main'])); // Default expand 'main'
  const [lastRefreshTime, setLastRefreshTime] = useState(null);

  // Fetch schemas from the backend
  const fetchSchemas = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get(`${apiBaseUrl}/schemas`, {
        params: { engine: selectedEngine }
      });
      
      setSchemas(response.data);
      setLastRefreshTime(new Date());
    } catch (err) {
      console.error('Failed to fetch schemas:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load schemas');
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, selectedEngine]);

  // Initial load and engine changes
  useEffect(() => {
    fetchSchemas();
  }, [fetchSchemas]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchSchemas, 30000);
    return () => clearInterval(interval);
  }, [fetchSchemas]);

  // Toggle dataset expansion
  const toggleDataset = useCallback((datasetId) => {
    setExpandedDatasets(prev => {
      const newSet = new Set(prev);
      if (newSet.has(datasetId)) {
        newSet.delete(datasetId);
      } else {
        newSet.add(datasetId);
      }
      return newSet;
    });
  }, []);

  // Get table type icon
  const getTableIcon = (tableType) => {
    switch (tableType?.toLowerCase()) {
      case 'view':
        return 'visibility';
      case 'table':
      default:
        return 'table_chart';
    }
  };

  // Format table name for display
  const formatTableName = (tableName) => {
    // Make the table name look more friendly
    return tableName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  // Handle table click (could be extended to show table details)
  const handleTableClick = useCallback((datasetId, tableId) => {
    console.log(`Clicked table: ${datasetId}.${tableId}`);
    // TODO: Could open table details, show preview, etc.
  }, []);

  // Handle engine change
  const handleEngineChange = useCallback((engine) => {
    setSelectedEngine(engine);
  }, []);

  // Handle manual refresh
  const handleRefresh = useCallback(() => {
    fetchSchemas();
  }, [fetchSchemas]);

  // Expose refresh method to parent components
  useImperativeHandle(ref, () => ({
    refreshSchemas: fetchSchemas
  }), [fetchSchemas]);

  if (loading && !schemas) {
    return (
      <div className="explorer-section">
        <div className="explorer-loading">
          <div className="spinner-small"></div>
          <span>Loading schemas...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="explorer-section">
        <div className="explorer-error">
          <div className="error-content">
            <span className="material-icons">error</span>
            <div>
              <div className="error-title">Failed to load schemas</div>
              <div className="error-message">{error}</div>
            </div>
          </div>
          <button className="retry-btn" onClick={handleRefresh}>
            <span className="material-icons">refresh</span>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="schema-explorer">
      {/* Engine Selector */}
      <div className="explorer-controls">
        <div className="engine-selector-mini">
          <select
            value={selectedEngine}
            onChange={(e) => handleEngineChange(e.target.value)}
            className="engine-select-small"
          >
            <option value="duckdb">DuckDB</option>
            <option value="clickhouse">ClickHouse</option>
          </select>
        </div>
        <button 
          className="refresh-btn" 
          onClick={handleRefresh}
          title="Refresh schemas"
          disabled={loading}
        >
          <span className={`material-icons ${loading ? 'spinning' : ''}`}>refresh</span>
        </button>
      </div>

      {/* Project Header */}
      <div className="explorer-section">
        <div className="explorer-item">
          <div className="explorer-item-header">
            <span className="material-icons expand-icon">expand_more</span>
            <span className="material-icons item-icon">cloud</span>
            <span className="item-text">bigquery-lite-project</span>
            <div className="project-info">
              <span className="engine-badge">{selectedEngine}</span>
            </div>
          </div>
        </div>

        {/* Datasets */}
        <div className="explorer-subsection">
          {schemas?.datasets?.map((dataset) => (
            <div key={dataset.dataset_id} className="dataset-container">
              <div 
                className="explorer-item nested dataset-item"
                onClick={() => toggleDataset(dataset.dataset_id)}
              >
                <div className="explorer-item-header">
                  <span className={`material-icons expand-icon ${expandedDatasets.has(dataset.dataset_id) ? 'expanded' : ''}`}>
                    expand_more
                  </span>
                  <span className="material-icons item-icon">storage</span>
                  <span className="item-text">{dataset.dataset_name}</span>
                  <div className="dataset-info">
                    <span className="table-count">{dataset.tables.length} tables</span>
                  </div>
                </div>
              </div>

              {/* Tables within dataset */}
              {expandedDatasets.has(dataset.dataset_id) && (
                <div className="tables-subsection">
                  {dataset.tables.map((table) => (
                    <div 
                      key={table.table_id} 
                      className="explorer-item table-item nested-deep"
                      onClick={() => handleTableClick(dataset.dataset_id, table.table_id)}
                    >
                      <div className="explorer-item-header">
                        <span className="table-spacer"></span>
                        <span className="material-icons item-icon table-icon">
                          {getTableIcon(table.table_type)}
                        </span>
                        <span className="item-text table-name">{table.table_name}</span>
                        <div className="table-actions">
                          <span className="table-type-badge">{table.table_type}</span>
                          <button className="item-action" title="More options">
                            <span className="material-icons">more_vert</span>
                          </button>
                        </div>
                      </div>
                      {table.columns.length > 0 && (
                        <div className="table-column-count">
                          {table.columns.length} columns
                        </div>
                      )}
                    </div>
                  ))}
                  
                  {dataset.tables.length === 0 && (
                    <div className="empty-dataset">
                      <span className="material-icons">table_chart</span>
                      <span>No tables in this dataset</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Schema Summary */}
        {schemas && (
          <div className="schema-summary">
            <div className="summary-stats">
              <div className="stat-item">
                <span className="stat-value">{schemas.total_datasets}</span>
                <span className="stat-label">Datasets</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{schemas.total_tables}</span>
                <span className="stat-label">Tables</span>
              </div>
            </div>
            {lastRefreshTime && (
              <div className="refresh-info">
                Last updated: {lastRefreshTime.toLocaleTimeString()}
              </div>
            )}
          </div>
        )}
      </div>

      {/* System Status */}
      {systemStatus && (
        <div className="explorer-section">
          <div className="status-section">
            <h4>System Status</h4>
            <div className="status-grid">
              <div className="status-item">
                <span className="status-label">Slots</span>
                <span className="status-value">{systemStatus.available_slots}/{systemStatus.total_slots}</span>
              </div>
              <div className="status-item">
                <span className="status-label">Queued</span>
                <span className="status-value">{systemStatus.queued_jobs}</span>
              </div>
              <div className="status-item">
                <span className="status-label">Running</span>
                <span className="status-value">{systemStatus.running_jobs}</span>
              </div>
              <div className="status-item">
                <span className="status-label">Completed</span>
                <span className="status-value">{systemStatus.completed_jobs}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

SchemaExplorer.displayName = 'SchemaExplorer';

export default SchemaExplorer;
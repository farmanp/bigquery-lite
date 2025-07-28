import React, { useState, forwardRef, useImperativeHandle } from 'react';
import SchemaBrowser from './SchemaBrowser';
import SchemaUpload from './SchemaUpload';
import SchemaExplorer from './SchemaExplorer';

const Sidebar = forwardRef(({ jobHistory, onLoadQuery, systemStatus, apiBaseUrl, onCreateTable, onViewSQL, onSchemaUploaded, isCollapsed, onToggleCollapse }, ref) => {
  const [activeSection, setActiveSection] = useState('explorer');
  const [searchQuery, setSearchQuery] = useState('');
  const schemaExplorerRef = React.useRef();

  // Expose refresh method to parent
  useImperativeHandle(ref, () => ({
    refreshSchemas: () => {
      if (schemaExplorerRef.current) {
        schemaExplorerRef.current.refreshSchemas();
      }
    }
  }), []);

  const sampleQueries = [
    {
      name: 'Simple Count',
      sql: 'SELECT COUNT(*) as total_rows FROM nyc_taxi;',
      description: 'Count total rows in dataset'
    },
    {
      name: 'Payment Analysis',
      sql: `SELECT 
    payment_type,
    COUNT(*) as trip_count,
    AVG(fare_amount) as avg_fare,
    SUM(total_amount) as total_revenue
FROM nyc_taxi 
WHERE fare_amount > 0 
GROUP BY payment_type 
ORDER BY trip_count DESC;`,
      description: 'Analyze trips by payment method'
    },
    {
      name: 'Hourly Patterns',
      sql: `SELECT 
    EXTRACT(hour FROM tpep_pickup_datetime) as hour,
    COUNT(*) as trip_count,
    AVG(fare_amount) as avg_fare
FROM nyc_taxi 
WHERE tpep_pickup_datetime IS NOT NULL
GROUP BY hour 
ORDER BY hour;`,
      description: 'Trip patterns by hour of day'
    },
    {
      name: 'Top Expensive Trips',
      sql: `SELECT 
    tpep_pickup_datetime,
    tpep_dropoff_datetime,
    trip_distance,
    fare_amount,
    total_amount
FROM nyc_taxi 
WHERE total_amount > 0 
ORDER BY total_amount DESC 
LIMIT 10;`,
      description: 'Find the most expensive trips'
    },
    {
      name: 'Distance Distribution',
      sql: `SELECT 
    CASE 
        WHEN trip_distance <= 1 THEN 'Short (≤1mi)'
        WHEN trip_distance <= 5 THEN 'Medium (1-5mi)'
        WHEN trip_distance <= 10 THEN 'Long (5-10mi)'
        ELSE 'Very Long (>10mi)'
    END as distance_category,
    COUNT(*) as trip_count,
    AVG(fare_amount) as avg_fare
FROM nyc_taxi 
WHERE trip_distance > 0 
GROUP BY distance_category 
ORDER BY trip_count DESC;`,
      description: 'Trip distribution by distance'
    }
  ];


  const getJobStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return { icon: 'check_circle', color: '#34a853' };
      case 'running':
        return { icon: 'refresh', color: '#fbbc04' };
      case 'failed':
        return { icon: 'error', color: '#ea4335' };
      default:
        return { icon: 'schedule', color: '#5f6368' };
    }
  };

  const formatJobTime = (timeString) => {
    if (!timeString) return '';
    const date = new Date(timeString);
    return date.toLocaleTimeString();
  };

  return (
    <div className="sidebar">
      {/* Sidebar Header */}
      <div className="sidebar-header">
        <div className="sidebar-title">
          <span className="material-icons">folder</span>
          <span>Explorer</span>
          <button 
            className="sidebar-collapse-btn"
            onClick={onToggleCollapse}
            title="Collapse left panel"
          >
            <span className="material-icons">keyboard_arrow_left</span>
          </button>
        </div>
        <div className="sidebar-header-actions">
          <button className="sidebar-action-btn">
            <span className="material-icons">add</span>
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="sidebar-search">
        <div className="search-container-sidebar">
          <span className="material-icons search-icon">search</span>
          <input
            type="text"
            placeholder="Search BigQuery resources"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input-sidebar"
          />
          <button className="filter-btn">
            <span className="material-icons">tune</span>
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="sidebar-tabs">
        <div
          className={`sidebar-tab ${activeSection === 'explorer' ? 'active' : ''}`}
          onClick={() => setActiveSection('explorer')}
        >
          Explorer
        </div>
        <div
          className={`sidebar-tab ${activeSection === 'schemas' ? 'active' : ''}`}
          onClick={() => setActiveSection('schemas')}
        >
          Schemas
        </div>
        <div
          className={`sidebar-tab ${activeSection === 'samples' ? 'active' : ''}`}
          onClick={() => setActiveSection('samples')}
        >
          Samples
        </div>
        <div
          className={`sidebar-tab ${activeSection === 'history' ? 'active' : ''}`}
          onClick={() => setActiveSection('history')}
        >
          History
        </div>
      </div>

      {/* Explorer Section */}
      {activeSection === 'explorer' && (
        <div className="sidebar-content">
          <SchemaExplorer 
            ref={schemaExplorerRef}
            apiBaseUrl={apiBaseUrl}
            systemStatus={systemStatus}
          />
        </div>
      )}

      {/* Schemas Section */}
      {activeSection === 'schemas' && (
        <div className="sidebar-content" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <SchemaUpload 
            apiBaseUrl={apiBaseUrl}
            onSchemaUploaded={onSchemaUploaded}
          />
          <div style={{ borderTop: '1px solid #e8eaed', paddingTop: '24px' }}>
            <SchemaBrowser 
              apiBaseUrl={apiBaseUrl}
              onCreateTable={onCreateTable}
              onViewSQL={onViewSQL}
            />
          </div>
        </div>
      )}

      {/* Sample Queries Section */}
      {activeSection === 'samples' && (
        <div className="sidebar-section">
          <h3>Sample Queries</h3>
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {sampleQueries.map((query, index) => (
              <div
                key={index}
                style={{
                  padding: '12px',
                  border: '1px solid #e8eaed',
                  borderRadius: '4px',
                  marginBottom: '8px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onClick={() => onLoadQuery(query.sql)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#f8f9fa';
                  e.currentTarget.style.borderColor = '#4285f4';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'white';
                  e.currentTarget.style.borderColor = '#e8eaed';
                }}
              >
                <div style={{ fontWeight: '500', marginBottom: '4px', color: '#3c4043' }}>
                  {query.name}
                </div>
                <div style={{ fontSize: '12px', color: '#5f6368', marginBottom: '8px' }}>
                  {query.description}
                </div>
                <div style={{ 
                  fontSize: '11px', 
                  fontFamily: 'monospace', 
                  color: '#5f6368',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {query.sql.length > 50 ? query.sql.substring(0, 50) + '...' : query.sql}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Job History Section */}
      {activeSection === 'history' && (
        <div className="sidebar-section">
          <h3>Query History</h3>
          <div className="job-history">
            {jobHistory.length === 0 ? (
              <div style={{ 
                padding: '20px', 
                textAlign: 'center', 
                color: '#5f6368',
                fontSize: '14px'
              }}>
                No queries executed yet
              </div>
            ) : (
              jobHistory.slice(0, 10).map((job) => {
                const statusInfo = getJobStatusIcon(job.status);
                return (
                  <div key={job.job_id} className="job-item">
                    <div className="job-header">
                      <div className="job-id">{job.job_id}</div>
                      <div 
                        className={`job-status ${job.status}`}
                        style={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: '4px' 
                        }}
                      >
                        <span 
                          className="material-icons" 
                          style={{ 
                            fontSize: '12px', 
                            color: statusInfo.color 
                          }}
                        >
                          {statusInfo.icon}
                        </span>
                        {job.status}
                      </div>
                    </div>
                    <div style={{ 
                      fontSize: '12px', 
                      color: '#5f6368', 
                      marginBottom: '4px' 
                    }}>
                      {job.engine} • {formatJobTime(job.created_at)}
                      {job.execution_time && (
                        <span> • {job.execution_time.toFixed(2)}s</span>
                      )}
                    </div>
                    <div className="job-preview">
                      {job.sql.length > 60 ? job.sql.substring(0, 60) + '...' : job.sql}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
});

Sidebar.displayName = 'Sidebar';

export default Sidebar;
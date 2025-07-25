import React, { useState } from 'react';

const Sidebar = ({ jobHistory, onLoadQuery, systemStatus }) => {
  const [activeSection, setActiveSection] = useState('datasets');

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

  const datasets = [
    {
      name: 'nyc_taxi',
      type: 'parquet',
      description: 'NYC Yellow Taxi trips (Jan 2023)',
      icon: 'local_taxi'
    },
    {
      name: 'sample_data',
      type: 'table',
      description: 'Generated sample dataset',
      icon: 'table_chart'
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
      {/* System Status */}
      {systemStatus && (
        <div className="sidebar-section">
          <h3>System Status</h3>
          <div style={{ fontSize: '14px', color: '#5f6368' }}>
            <div style={{ marginBottom: '8px' }}>
              <strong>Slots:</strong> {systemStatus.available_slots}/{systemStatus.total_slots} available
            </div>
            <div style={{ marginBottom: '8px' }}>
              <strong>Queued:</strong> {systemStatus.queued_jobs} jobs
            </div>
            <div style={{ marginBottom: '8px' }}>
              <strong>Running:</strong> {systemStatus.running_jobs} jobs
            </div>
            <div>
              <strong>Completed:</strong> {systemStatus.completed_jobs} jobs
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #e8eaed' }}>
        <div
          style={{
            flex: 1,
            padding: '12px 16px',
            cursor: 'pointer',
            borderBottom: activeSection === 'datasets' ? '2px solid #4285f4' : '2px solid transparent',
            color: activeSection === 'datasets' ? '#4285f4' : '#5f6368',
            fontWeight: '500',
            fontSize: '14px',
            textAlign: 'center'
          }}
          onClick={() => setActiveSection('datasets')}
        >
          Data
        </div>
        <div
          style={{
            flex: 1,
            padding: '12px 16px',
            cursor: 'pointer',
            borderBottom: activeSection === 'samples' ? '2px solid #4285f4' : '2px solid transparent',
            color: activeSection === 'samples' ? '#4285f4' : '#5f6368',
            fontWeight: '500',
            fontSize: '14px',
            textAlign: 'center'
          }}
          onClick={() => setActiveSection('samples')}
        >
          Samples
        </div>
        <div
          style={{
            flex: 1,
            padding: '12px 16px',
            cursor: 'pointer',
            borderBottom: activeSection === 'history' ? '2px solid #4285f4' : '2px solid transparent',
            color: activeSection === 'history' ? '#4285f4' : '#5f6368',
            fontWeight: '500',
            fontSize: '14px',
            textAlign: 'center'
          }}
          onClick={() => setActiveSection('history')}
        >
          History
        </div>
      </div>

      {/* Datasets Section */}
      {activeSection === 'datasets' && (
        <div className="sidebar-section">
          <h3>Available Datasets</h3>
          <ul className="dataset-list">
            {datasets.map((dataset) => (
              <li key={dataset.name} className="dataset-item">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="material-icons" style={{ fontSize: '20px', color: '#5f6368' }}>
                    {dataset.icon}
                  </span>
                  <div>
                    <div style={{ fontWeight: '500', color: '#3c4043' }}>
                      {dataset.name}
                    </div>
                    <div style={{ fontSize: '12px', color: '#5f6368' }}>
                      {dataset.description}
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
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
};

export default Sidebar;
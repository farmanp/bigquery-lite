import React from 'react';
import ResultsTable from './ResultsTable';
import QueryPlan from './QueryPlan';

const ResultsPanel = ({ 
  results, 
  queryPlan, 
  error, 
  isLoading, 
  currentJob, 
  activeTab, 
  onTabChange 
}) => {
  const renderTabContent = () => {
    if (error) {
      return (
        <div className="tab-content">
          <div className="error-message">
            <strong>Query Error:</strong><br />
            {error}
          </div>
        </div>
      );
    }

    if (isLoading) {
      return (
        <div className="tab-content">
          <div className="loading-spinner">
            <div className="spinner"></div>
            <div>
              {currentJob ? (
                <div>
                  <div>Executing query...</div>
                  <div style={{ fontSize: '12px', color: '#5f6368', marginTop: '8px' }}>
                    Job ID: {currentJob.job_id}
                  </div>
                  {currentJob.status && (
                    <div style={{ fontSize: '12px', color: '#5f6368' }}>
                      Status: {currentJob.status}
                    </div>
                  )}
                </div>
              ) : (
                'Submitting query...'
              )}
            </div>
          </div>
        </div>
      );
    }

    switch (activeTab) {
      case 'results':
        return (
          <div className="tab-content">
            {results ? (
              <ResultsTable results={results} />
            ) : (
              <div style={{ padding: '32px 16px', textAlign: 'center', color: '#5f6368' }}>
                <span className="material-icons" style={{ fontSize: '48px', marginBottom: '16px', display: 'block' }}>
                  table_chart
                </span>
                <div>No query results yet</div>
                <div style={{ fontSize: '14px', marginTop: '8px' }}>
                  Run a query to see results here
                </div>
              </div>
            )}
          </div>
        );
      
      case 'plan':
        return (
          <div className="tab-content">
            {queryPlan ? (
              <QueryPlan plan={queryPlan} />
            ) : (
              <div style={{ padding: '32px 16px', textAlign: 'center', color: '#5f6368' }}>
                <span className="material-icons" style={{ fontSize: '48px', marginBottom: '16px', display: 'block' }}>
                  account_tree
                </span>
                <div>No execution plan available</div>
                <div style={{ fontSize: '14px', marginTop: '8px' }}>
                  Run a query to see the execution plan
                </div>
              </div>
            )}
          </div>
        );
      
      default:
        return <div className="tab-content">Invalid tab</div>;
    }
  };

  const getResultsInfo = () => {
    if (!results || error || isLoading) return null;

    const rowCount = results.data ? results.data.length : 0;
    const executionTime = results.execution_time || queryPlan?.execution_time;
    const engine = results.engine || queryPlan?.engine;
    const memoryUsed = queryPlan?.memory_used_mb;

    return (
      <div className="results-info">
        <div className="execution-stats">
          <div className="stat-item">
            <span className="material-icons">table_rows</span>
            <span>{rowCount.toLocaleString()} rows</span>
          </div>
          
          {executionTime && (
            <div className="stat-item">
              <span className="material-icons">schedule</span>
              <span>{executionTime.toFixed(3)}s</span>
            </div>
          )}
          
          {engine && (
            <div className="stat-item">
              <span className="material-icons">storage</span>
              <span>{engine.toUpperCase()}</span>
            </div>
          )}
          
          {memoryUsed && (
            <div className="stat-item">
              <span className="material-icons">memory</span>
              <span>{memoryUsed.toFixed(1)} MB</span>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="results-section">
      <div className="results-tabs">
        <div 
          className={`tab ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => onTabChange('results')}
        >
          <span className="material-icons" style={{ marginRight: '8px', fontSize: '18px' }}>
            table_chart
          </span>
          Results
        </div>
        <div 
          className={`tab ${activeTab === 'plan' ? 'active' : ''}`}
          onClick={() => onTabChange('plan')}
        >
          <span className="material-icons" style={{ marginRight: '8px', fontSize: '18px' }}>
            account_tree
          </span>
          Execution Details
        </div>
      </div>
      
      {getResultsInfo()}
      
      {renderTabContent()}
    </div>
  );
};

export default ResultsPanel;
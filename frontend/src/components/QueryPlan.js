import React from 'react';

const QueryPlan = ({ plan }) => {
  if (!plan) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#5f6368' }}>
        <span className="material-icons" style={{ fontSize: '48px', marginBottom: '16px', display: 'block' }}>
          account_tree
        </span>
        <div>No execution plan available</div>
      </div>
    );
  }

  const formatExecutionTime = (time) => {
    if (time < 0.001) return '<1ms';
    if (time < 1) return `${(time * 1000).toFixed(0)}ms`;
    return `${time.toFixed(3)}s`;
  };

  const formatMemory = (mb) => {
    if (mb < 1) return `${(mb * 1024).toFixed(0)} KB`;
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  const formatNumber = (num) => {
    if (num === undefined || num === null) return 'N/A';
    return num.toLocaleString();
  };

  return (
    <div className="query-plan-container" style={{ padding: '16px', height: '100%', overflow: 'auto' }}>
      {/* Execution Summary */}
      <div style={{ 
        background: '#f8f9fa', 
        border: '1px solid #e8eaed', 
        borderRadius: '8px', 
        padding: '16px', 
        marginBottom: '24px' 
      }}>
        <h3 style={{ margin: '0 0 16px 0', color: '#3c4043' }}>Execution Summary</h3>
        
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '16px' 
        }}>
          <div>
            <div style={{ fontSize: '12px', color: '#5f6368', marginBottom: '4px' }}>
              EXECUTION TIME
            </div>
            <div style={{ fontSize: '18px', fontWeight: '500', color: '#3c4043' }}>
              {plan.execution_time ? formatExecutionTime(plan.execution_time) : 'N/A'}
            </div>
          </div>
          
          <div>
            <div style={{ fontSize: '12px', color: '#5f6368', marginBottom: '4px' }}>
              MEMORY USED
            </div>
            <div style={{ fontSize: '18px', fontWeight: '500', color: '#3c4043' }}>
              {plan.memory_used_mb ? formatMemory(plan.memory_used_mb) : 'N/A'}
            </div>
          </div>
          
          <div>
            <div style={{ fontSize: '12px', color: '#5f6368', marginBottom: '4px' }}>
              ROWS PROCESSED
            </div>
            <div style={{ fontSize: '18px', fontWeight: '500', color: '#3c4043' }}>
              {formatNumber(plan.rows_processed)}
            </div>
          </div>
          
          <div>
            <div style={{ fontSize: '12px', color: '#5f6368', marginBottom: '4px' }}>
              ENGINE
            </div>
            <div style={{ fontSize: '18px', fontWeight: '500', color: '#3c4043' }}>
              {plan.engine ? plan.engine.toUpperCase() : 'N/A'}
            </div>
          </div>
          
          {plan.slots_used && (
            <div>
              <div style={{ fontSize: '12px', color: '#5f6368', marginBottom: '4px' }}>
                SLOTS USED
              </div>
              <div style={{ fontSize: '18px', fontWeight: '500', color: '#3c4043' }}>
                {plan.slots_used}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Query Plan Details */}
      {plan.query_plan && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 16px 0', color: '#3c4043' }}>Query Execution Plan</h3>
          <div className="query-plan">
            {typeof plan.query_plan === 'string' ? plan.query_plan : JSON.stringify(plan.query_plan, null, 2)}
          </div>
        </div>
      )}

      {/* Performance Metrics */}
      {(plan.cpu_time || plan.io_wait || plan.network_time) && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 16px 0', color: '#3c4043' }}>Performance Breakdown</h3>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
            gap: '12px' 
          }}>
            {plan.cpu_time && (
              <div style={{ 
                background: '#e3f2fd', 
                padding: '12px', 
                borderRadius: '4px',
                borderLeft: '4px solid #2196f3'
              }}>
                <div style={{ fontSize: '12px', color: '#1565c0', marginBottom: '4px' }}>
                  CPU TIME
                </div>
                <div style={{ fontSize: '16px', fontWeight: '500', color: '#0d47a1' }}>
                  {formatExecutionTime(plan.cpu_time)}
                </div>
              </div>
            )}
            
            {plan.io_wait && (
              <div style={{ 
                background: '#fff3e0', 
                padding: '12px', 
                borderRadius: '4px',
                borderLeft: '4px solid #ff9800'
              }}>
                <div style={{ fontSize: '12px', color: '#e65100', marginBottom: '4px' }}>
                  I/O WAIT
                </div>
                <div style={{ fontSize: '16px', fontWeight: '500', color: '#bf360c' }}>
                  {formatExecutionTime(plan.io_wait)}
                </div>
              </div>
            )}
            
            {plan.network_time && (
              <div style={{ 
                background: '#f3e5f5', 
                padding: '12px', 
                borderRadius: '4px',
                borderLeft: '4px solid #9c27b0'
              }}>
                <div style={{ fontSize: '12px', color: '#6a1b9a', marginBottom: '4px' }}>
                  NETWORK
                </div>
                <div style={{ fontSize: '16px', fontWeight: '500', color: '#4a148c' }}>
                  {formatExecutionTime(plan.network_time)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Raw Execution Stats */}
      <div>
        <h3 style={{ margin: '0 0 16px 0', color: '#3c4043' }}>Raw Execution Statistics</h3>
        
        <div style={{ 
          background: '#f8f9fa', 
          border: '1px solid #e8eaed', 
          borderRadius: '4px', 
          padding: '16px',
          fontFamily: 'monospace',
          fontSize: '13px',
          lineHeight: '1.5',
          overflow: 'auto'
        }}>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(plan, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default QueryPlan;
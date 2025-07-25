import React from 'react';

const Header = ({ systemStatus, isExecuting }) => {
  return (
    <div className="header">
      <h1>BigQuery-Lite</h1>
      
      <div className="header-controls">
        {systemStatus && (
          <div className="status-indicator">
            <div className="status-dot"></div>
            <span>
              {systemStatus.available_slots}/{systemStatus.total_slots} slots available
            </span>
          </div>
        )}
        
        {isExecuting && (
          <div className="status-indicator">
            <div className="spinner"></div>
            <span>Query running...</span>
          </div>
        )}
        
        <div className="status-indicator">
          <span className="material-icons">info</span>
          <span>Local Environment</span>
        </div>
      </div>
    </div>
  );
};

export default Header;
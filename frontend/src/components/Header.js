import React, { useState } from 'react';

const Header = ({ systemStatus, isExecuting }) => {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="header">
      <div className="header-left">
        <div className="header-brand">
          <span className="material-icons" style={{ fontSize: '24px', marginRight: '8px', color: '#1a73e8' }}>analytics</span>
          <h1>BigQuery-Lite</h1>
        </div>
        
        <div className="header-search">
          <div className="search-container">
            <span className="material-icons search-icon">search</span>
            <input
              type="text"
              placeholder="Search for resources across projects"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>
        </div>
      </div>
      
      <div className="header-controls">
        {systemStatus && (
          <div className="status-indicator">
            <div className="status-dot"></div>
            <span>
              {systemStatus.available_slots}/{systemStatus.total_slots} slots
            </span>
          </div>
        )}
        
        {isExecuting && (
          <div className="status-indicator">
            <div className="spinner"></div>
            <span>Running...</span>
          </div>
        )}
        
        <div className="header-actions">
          <button className="header-button">
            <span className="material-icons">help_outline</span>
          </button>
          <button className="header-button">
            <span className="material-icons">settings</span>
          </button>
          <button className="header-button">
            <span className="material-icons">account_circle</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Header;
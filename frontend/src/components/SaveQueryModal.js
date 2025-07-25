import React, { useState } from 'react';
import './SaveQueryModal.css';

const SaveQueryModal = ({ isOpen, onClose, onSave, initialName = '' }) => {
  const [queryName, setQueryName] = useState(initialName);

  const handleSave = () => {
    if (queryName.trim()) {
      onSave(queryName.trim());
      onClose();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="save-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Save Query</h3>
          <button 
            className="close-btn"
            onClick={onClose}
          >
            <span className="material-icons">close</span>
          </button>
        </div>
        
        <div className="modal-body">
          <div className="form-group">
            <label htmlFor="query-name">Query Name:</label>
            <input
              id="query-name"
              type="text"
              value={queryName}
              onChange={(e) => setQueryName(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Enter a name for your query"
              autoFocus
            />
          </div>
        </div>
        
        <div className="modal-footer">
          <button 
            className="bq-button secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button 
            className="bq-button"
            onClick={handleSave}
            disabled={!queryName.trim()}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
};

export default SaveQueryModal;
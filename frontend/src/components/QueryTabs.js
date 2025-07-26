import React, { useState } from 'react';
import SaveQueryModal from './SaveQueryModal';
import './QueryTabs.css';

const QueryTabs = ({ 
  tabs, 
  activeTabId, 
  onTabChange, 
  onTabClose, 
  onNewTab,
  onTabSave 
}) => {
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [savingTabId, setSavingTabId] = useState(null);
  const handleTabClick = (tabId, e) => {
    e.stopPropagation();
    onTabChange(tabId);
  };

  const handleCloseClick = (tabId, e) => {
    e.stopPropagation();
    onTabClose(tabId);
  };

  const handleSaveClick = (tabId, e) => {
    e.stopPropagation();
    setSavingTabId(tabId);
    setSaveModalOpen(true);
  };

  const handleSaveConfirm = (name) => {
    if (savingTabId) {
      onTabSave(savingTabId, name);
      setSavingTabId(null);
    }
  };

  const handleSaveCancel = () => {
    setSaveModalOpen(false);
    setSavingTabId(null);
  };

  return (
    <>
      <div className="query-tabs">
        <div className="tabs-container">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              className={`tab ${tab.id === activeTabId ? 'active' : ''} ${tab.isUnsaved ? 'unsaved' : ''}`}
              onClick={(e) => handleTabClick(tab.id, e)}
            >
              <div className="tab-content">
                <span className="tab-title">
                  {tab.name || 'Untitled query'}
                  {tab.isUnsaved && <span className="unsaved-indicator">*</span>}
                </span><div className="tab-actions">
                  {tab.isUnsaved && (
                    <button
                      className="tab-action-btn save-btn"
                      onClick={(e) => handleSaveClick(tab.id, e)}
                      title="Save query"
                    >
                      <span className="material-icons">save</span>
                    </button>
                  )}
                  
                  <button
                    className="tab-action-btn close-btn"
                    onClick={(e) => handleCloseClick(tab.id, e)}
                    title="Close tab"
                  >
                    ❌
                  </button>
                </div>
              </div>
            </div>
          ))}
          
          <button 
            className="new-tab-btn"
            onClick={onNewTab}
            title="New query"
          >
            <span className="material-icons">add</span>
          </button>
        </div>
      </div>
      
      <SaveQueryModal
        isOpen={saveModalOpen}
        onClose={handleSaveCancel}
        onSave={handleSaveConfirm}
        initialName={tabs.find(tab => tab.id === savingTabId)?.name || ''}
      />
    </>
  );
};

export default QueryTabs;
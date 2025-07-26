import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import SQLEditor from './components/SQLEditor';
import ResultsPanel from './components/ResultsPanel';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import QueryTabs from './components/QueryTabs';
import TableCreation from './components/TableCreation';
import SQLViewer from './components/SQLViewer';
import './App.css';

// Determine API base URL based on environment
const getApiBaseUrl = () => {
  // If running in Docker, use the proxy path
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return '/api';
  }
  // Development mode - use environment variable or default to localhost
  return process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001';
};

const API_BASE_URL = getApiBaseUrl();

// Helper function to generate unique tab ID
const generateTabId = () => `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// Helper function to create a new tab
const createNewTab = (name = null, isFirstTab = false) => ({
  id: generateTabId(),
  name: name,
  queryText: isFirstTab ? '-- Welcome to BigQuery-Lite!\n-- Try running this sample query:\n\nSELECT COUNT(*) as total_rows FROM nyc_taxi;' : '',
  selectedEngine: 'duckdb',
  isExecuting: false,
  currentJob: null,
  queryResults: null,
  queryPlan: null,
  queryError: null,
  isUnsaved: false,
  savedQuery: null
});

function App() {
  const [tabs, setTabs] = useState([createNewTab('Untitled query', true)]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [jobHistory, setJobHistory] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('results');
  
  // Schema management state
  const [showTableCreation, setShowTableCreation] = useState(false);
  const [showSQLViewer, setShowSQLViewer] = useState(false);
  const [selectedSchema, setSelectedSchema] = useState(null);
  const [selectedEngine, setSelectedEngine] = useState('duckdb');
  
  // Get current active tab
  const currentTab = tabs.find(tab => tab.id === activeTabId) || tabs[0];
  
  // Initialize activeTabId if tabs exist but no active tab is set
  useEffect(() => {
    if (tabs.length > 0 && (!activeTabId || !tabs.find(tab => tab.id === activeTabId))) {
      setActiveTabId(tabs[0].id);
    }
  }, [tabs, activeTabId]);

  // Fetch system status periodically
  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/status`);
        setSystemStatus(response.data);
      } catch (error) {
        console.error('Failed to fetch system status:', error);
      }
    };

    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  // Poll for job updates when a job is running
  useEffect(() => {
    if (!currentTab?.currentJob || currentTab?.currentJob?.status === 'completed' || currentTab?.currentJob?.status === 'failed') {
      return;
    }

    const pollJob = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/jobs/${currentTab.currentJob.job_id}`);
        const jobData = response.data;
        
        // Update the current tab with job data
        setTabs(prevTabs => prevTabs.map(tab => 
          tab.id === activeTabId 
            ? { ...tab, currentJob: jobData }
            : tab
        ));
        
        if (jobData.status === 'completed') {
          // Fetch results
          const resultResponse = await axios.get(`${API_BASE_URL}/jobs/${currentTab.currentJob.job_id}/result`);
          const result = resultResponse.data;
          
          // Update tab with results
          setTabs(prevTabs => prevTabs.map(tab => 
            tab.id === activeTabId 
              ? { 
                  ...tab, 
                  queryResults: result.result,
                  queryPlan: result.execution_stats,
                  isExecuting: false
                }
              : tab
          ));
          
          // Update job history
          setJobHistory(prev => [jobData, ...prev.filter(j => j.job_id !== jobData.job_id)]);
        } else if (jobData.status === 'failed') {
          // Update tab with error
          setTabs(prevTabs => prevTabs.map(tab => 
            tab.id === activeTabId 
              ? { 
                  ...tab, 
                  queryError: jobData.error,
                  isExecuting: false
                }
              : tab
          ));
          setJobHistory(prev => [jobData, ...prev.filter(j => j.job_id !== jobData.job_id)]);
        }
      } catch (error) {
        console.error('Failed to poll job status:', error);
        setTabs(prevTabs => prevTabs.map(tab => 
          tab.id === activeTabId 
            ? { ...tab, isExecuting: false }
            : tab
        ));
      }
    };

    const interval = setInterval(pollJob, 1000); // Poll every second
    return () => clearInterval(interval);
  }, [currentTab?.currentJob, activeTabId]);

  const executeQuery = useCallback(async () => {
    if (!currentTab?.queryText.trim() || currentTab?.isExecuting) return;

    // Update current tab execution state
    setTabs(prevTabs => prevTabs.map(tab => 
      tab.id === activeTabId 
        ? { 
            ...tab, 
            isExecuting: true,
            queryResults: null,
            queryPlan: null,
            queryError: null
          }
        : tab
    ));
    setActiveTab('results');

    try {
      const response = await axios.post(`${API_BASE_URL}/queries`, {
        sql: currentTab.queryText,
        engine: currentTab.selectedEngine,
        priority: 1,
        estimated_slots: 1
      });

      const jobData = response.data;
      setTabs(prevTabs => prevTabs.map(tab => 
        tab.id === activeTabId 
          ? { ...tab, currentJob: { job_id: jobData.job_id, status: 'submitted' } }
          : tab
      ));
      
    } catch (error) {
      setTabs(prevTabs => prevTabs.map(tab => 
        tab.id === activeTabId 
          ? { 
              ...tab, 
              queryError: error.response?.data?.detail || error.message,
              isExecuting: false
            }
          : tab
      ));
    }
  }, [currentTab, activeTabId]);

  const loadSampleQuery = useCallback((query) => {
    setTabs(prevTabs => prevTabs.map(tab => 
      tab.id === activeTabId 
        ? { ...tab, queryText: query, isUnsaved: true }
        : tab
    ));
  }, [activeTabId]);

  const formatQuery = useCallback(() => {
    if (!currentTab) return;
    
    // Improved SQL formatting that preserves comments
    let formatted = currentTab.queryText;
    
    // Split by lines to handle comments properly
    const lines = formatted.split('\n');
    const processedLines = [];
    
    for (let line of lines) {
      const trimmedLine = line.trim();
      
      // Preserve comment lines as-is
      if (trimmedLine.startsWith('--')) {
        processedLines.push(trimmedLine);
        continue;
      }
      
      // Skip empty lines
      if (!trimmedLine) {
        continue;
      }
      
      // Process SQL lines
      let processedLine = trimmedLine
        // Normalize whitespace within the line (but preserve structure)
        .replace(/\s+/g, ' ')
        // Add proper spacing around operators
        .replace(/,/g, ', ')
        .replace(/=/g, ' = ')
        .replace(/</g, ' < ')
        .replace(/>/g, ' > ')
        // Clean up any double spaces created
        .replace(/\s+/g, ' ');
      
      // Add proper line breaks for SQL keywords
      processedLine = processedLine
        .replace(/\bFROM\b/gi, '\nFROM')
        .replace(/\bWHERE\b/gi, '\nWHERE')
        .replace(/\bGROUP BY\b/gi, '\nGROUP BY')
        .replace(/\bORDER BY\b/gi, '\nORDER BY')
        .replace(/\bHAVING\b/gi, '\nHAVING')
        .replace(/\bLIMIT\b/gi, '\nLIMIT')
        .replace(/\bJOIN\b/gi, '\nJOIN')
        .replace(/\bINNER JOIN\b/gi, '\nINNER JOIN')
        .replace(/\bLEFT JOIN\b/gi, '\nLEFT JOIN')
        .replace(/\bRIGHT JOIN\b/gi, '\nRIGHT JOIN')
        .replace(/\bFULL JOIN\b/gi, '\nFULL JOIN')
        .replace(/\bUNION\b/gi, '\nUNION')
        .replace(/\bUNION ALL\b/gi, '\nUNION ALL');
      
      processedLines.push(processedLine);
    }
    
    // Join lines and clean up extra newlines
    formatted = processedLines
      .join('\n')
      .replace(/\n\s*\n/g, '\n')  // Remove multiple empty lines
      .replace(/^\n+/, '')        // Remove leading newlines
      .replace(/\n+$/, '');       // Remove trailing newlines
    
    setTabs(prevTabs => prevTabs.map(tab => 
      tab.id === activeTabId 
        ? { ...tab, queryText: formatted, isUnsaved: true }
        : tab
    ));
  }, [currentTab, activeTabId]);

  const clearResults = useCallback(() => {
    setTabs(prevTabs => prevTabs.map(tab => 
      tab.id === activeTabId 
        ? { 
            ...tab, 
            queryResults: null,
            queryPlan: null,
            queryError: null
          }
        : tab
    ));
  }, [activeTabId]);

  // Tab management functions
  const handleTabChange = useCallback((tabId) => {
    setActiveTabId(tabId);
  }, []);

  const handleNewTab = useCallback(() => {
    const newTab = createNewTab();
    setTabs(prevTabs => [...prevTabs, newTab]);
    setActiveTabId(newTab.id);
  }, []);

  const handleTabClose = useCallback((tabId) => {
    setTabs(prevTabs => {
      const filteredTabs = prevTabs.filter(tab => tab.id !== tabId);
      
      // If we're closing the active tab, switch to another one
      if (tabId === activeTabId) {
        const tabIndex = prevTabs.findIndex(tab => tab.id === tabId);
        const newActiveTab = filteredTabs[tabIndex] || filteredTabs[tabIndex - 1] || filteredTabs[0];
        if (newActiveTab) {
          setActiveTabId(newActiveTab.id);
        }
      }
      
      // Ensure at least one tab remains
      if (filteredTabs.length === 0) {
        const newTab = createNewTab('Untitled query', true);
        setActiveTabId(newTab.id);
        return [newTab];
      }
      
      return filteredTabs;
    });
  }, [activeTabId]);

  const handleTabSave = useCallback((tabId, name) => {
    setTabs(prevTabs => prevTabs.map(tab => 
      tab.id === tabId 
        ? { 
            ...tab, 
            name: name || tab.name,
            isUnsaved: false, 
            savedQuery: tab.queryText 
          }
        : tab
    ));
  }, []);

  const handleQueryTextChange = useCallback((newText) => {
    setTabs(prevTabs => prevTabs.map(tab => 
      tab.id === activeTabId 
        ? { 
            ...tab, 
            queryText: newText,
            isUnsaved: tab.savedQuery !== newText
          }
        : tab
    ));
  }, [activeTabId]);

  const handleEngineChange = useCallback((engine) => {
    setTabs(prevTabs => prevTabs.map(tab => 
      tab.id === activeTabId 
        ? { ...tab, selectedEngine: engine }
        : tab
    ));
  }, [activeTabId]);

  // Schema management handlers
  const handleCreateTable = useCallback((schemaName, engine) => {
    setSelectedSchema(schemaName);
    setSelectedEngine(engine);
    setShowTableCreation(true);
  }, []);

  const handleViewSQL = useCallback((schemaName, engine) => {
    setSelectedSchema(schemaName);
    setSelectedEngine(engine);
    setShowSQLViewer(true);
  }, []);

  const handleSchemaUploaded = useCallback((schema) => {
    // Could refresh the schema browser or show a notification
    console.log('Schema uploaded:', schema);
  }, []);

  const handleTableCreated = useCallback((tableInfo) => {
    console.log('Table created:', tableInfo);
    setShowTableCreation(false);
  }, []);

  const handleExecuteSQL = useCallback((sql, engine) => {
    // Add SQL to current tab and execute
    setTabs(prevTabs => prevTabs.map(tab => 
      tab.id === activeTabId 
        ? { 
            ...tab, 
            queryText: sql, 
            selectedEngine: engine,
            isUnsaved: true 
          }
        : tab
    ));
    setShowSQLViewer(false);
    // Execute after a brief delay to allow state to update
    setTimeout(() => executeQuery(), 100);
  }, [activeTabId, executeQuery]);

  return (
    <div className="app">
      <Header 
        systemStatus={systemStatus}
        isExecuting={currentTab?.isExecuting}
      />
      
      <div className="main-content">
        <Sidebar 
          jobHistory={jobHistory}
          onLoadQuery={loadSampleQuery}
          systemStatus={systemStatus}
          apiBaseUrl={API_BASE_URL}
          onCreateTable={handleCreateTable}
          onViewSQL={handleViewSQL}
          onSchemaUploaded={handleSchemaUploaded}
        />
        
        <div className="workspace">
          <QueryTabs
            tabs={tabs}
            activeTabId={activeTabId}
            onTabChange={handleTabChange}
            onTabClose={handleTabClose}
            onNewTab={handleNewTab}
            onTabSave={handleTabSave}
          />
          
          <div className="query-editor-section">
            <div className="editor-header">
              <div className="editor-controls">
                <div className="engine-selector">
                  <label htmlFor="engine-select">Engine:</label>
                  <select
                    id="engine-select"
                    className="bq-select"
                    value={currentTab?.selectedEngine || 'duckdb'}
                    onChange={(e) => handleEngineChange(e.target.value)}
                    disabled={currentTab?.isExecuting}
                  >
                    <option value="duckdb">DuckDB (Interactive)</option>
                    <option value="clickhouse">ClickHouse (Distributed)</option>
                  </select>
                </div>
              </div>
              
              <div className="editor-controls">
                <button
                  className="bq-button secondary"
                  onClick={formatQuery}
                  disabled={currentTab?.isExecuting}
                >
                  <span className="material-icons">code</span>
                  Format
                </button>
                
                <button
                  className="bq-button secondary"
                  onClick={clearResults}
                >
                  <span className="material-icons">clear</span>
                  Clear
                </button>
                
                <button
                  className="bq-button"
                  onClick={executeQuery}
                  disabled={currentTab?.isExecuting || !currentTab?.queryText.trim()}
                >
                  {currentTab?.isExecuting ? (
                    <>
                      <div className="spinner"></div>
                      Running...
                    </>
                  ) : (
                    <>
                      <span className="material-icons">play_arrow</span>
                      Run Query
                    </>
                  )}
                </button>
              </div>
            </div>
            
            <SQLEditor
              value={currentTab?.queryText || ''}
              onChange={handleQueryTextChange}
              onExecute={executeQuery}
              disabled={currentTab?.isExecuting}
            />
          </div>
          
          <ResultsPanel
            results={currentTab?.queryResults}
            queryPlan={currentTab?.queryPlan}
            error={currentTab?.queryError}
            isLoading={currentTab?.isExecuting}
            currentJob={currentTab?.currentJob}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />
        </div>
      </div>

      {/* Schema Management Modals */}
      {showTableCreation && (
        <TableCreation
          apiBaseUrl={API_BASE_URL}
          schemaName={selectedSchema}
          onTableCreated={handleTableCreated}
          onClose={() => setShowTableCreation(false)}
        />
      )}

      {showSQLViewer && (
        <SQLViewer
          apiBaseUrl={API_BASE_URL}
          schemaName={selectedSchema}
          engine={selectedEngine}
          onClose={() => setShowSQLViewer(false)}
          onExecuteSQL={handleExecuteSQL}
        />
      )}
    </div>
  );
}

export default App;
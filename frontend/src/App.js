import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import SQLEditor from './components/SQLEditor';
import ResultsPanel from './components/ResultsPanel';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
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

function App() {
  const [queryText, setQueryText] = useState('-- Welcome to BigQuery-Lite!\n-- Try running this sample query:\n\nSELECT COUNT(*) as total_rows FROM nyc_taxi;');
  const [selectedEngine, setSelectedEngine] = useState('duckdb');
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentJob, setCurrentJob] = useState(null);
  const [queryResults, setQueryResults] = useState(null);
  const [queryPlan, setQueryPlan] = useState(null);
  const [queryError, setQueryError] = useState(null);
  const [jobHistory, setJobHistory] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('results');

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
    if (!currentJob || currentJob.status === 'completed' || currentJob.status === 'failed') {
      return;
    }

    const pollJob = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/jobs/${currentJob.job_id}`);
        const jobData = response.data;
        
        setCurrentJob(jobData);
        
        if (jobData.status === 'completed') {
          // Fetch results
          const resultResponse = await axios.get(`${API_BASE_URL}/jobs/${currentJob.job_id}/result`);
          const result = resultResponse.data;
          
          setQueryResults(result.result);
          setQueryPlan(result.execution_stats);
          setIsExecuting(false);
          
          // Update job history
          setJobHistory(prev => [jobData, ...prev.filter(j => j.job_id !== jobData.job_id)]);
        } else if (jobData.status === 'failed') {
          setQueryError(jobData.error);
          setIsExecuting(false);
          setJobHistory(prev => [jobData, ...prev.filter(j => j.job_id !== jobData.job_id)]);
        }
      } catch (error) {
        console.error('Failed to poll job status:', error);
        setIsExecuting(false);
      }
    };

    const interval = setInterval(pollJob, 1000); // Poll every second
    return () => clearInterval(interval);
  }, [currentJob]);

  const executeQuery = useCallback(async () => {
    if (!queryText.trim() || isExecuting) return;

    setIsExecuting(true);
    setQueryResults(null);
    setQueryPlan(null);
    setQueryError(null);
    setActiveTab('results');

    try {
      const response = await axios.post(`${API_BASE_URL}/queries`, {
        sql: queryText,
        engine: selectedEngine,
        priority: 1,
        estimated_slots: 1
      });

      const jobData = response.data;
      setCurrentJob({ job_id: jobData.job_id, status: 'submitted' });
      
    } catch (error) {
      setQueryError(error.response?.data?.detail || error.message);
      setIsExecuting(false);
    }
  }, [queryText, selectedEngine, isExecuting]);

  const loadSampleQuery = useCallback((query) => {
    setQueryText(query);
  }, []);

  const formatQuery = useCallback(() => {
    // Simple SQL formatting - you could integrate a proper SQL formatter here
    const formatted = queryText
      .replace(/\s+/g, ' ')
      .replace(/,/g, ',\n    ')
      .replace(/\bFROM\b/gi, '\nFROM')
      .replace(/\bWHERE\b/gi, '\nWHERE')
      .replace(/\bGROUP BY\b/gi, '\nGROUP BY')
      .replace(/\bORDER BY\b/gi, '\nORDER BY')
      .replace(/\bHAVING\b/gi, '\nHAVING')
      .replace(/\bLIMIT\b/gi, '\nLIMIT');
    
    setQueryText(formatted);
  }, [queryText]);

  const clearResults = useCallback(() => {
    setQueryResults(null);
    setQueryPlan(null);
    setQueryError(null);
  }, []);

  return (
    <div className="app">
      <Header 
        systemStatus={systemStatus}
        isExecuting={isExecuting}
      />
      
      <div className="main-content">
        <Sidebar 
          jobHistory={jobHistory}
          onLoadQuery={loadSampleQuery}
          systemStatus={systemStatus}
        />
        
        <div className="workspace">
          <div className="query-editor-section">
            <div className="editor-header">
              <div className="editor-controls">
                <div className="engine-selector">
                  <label htmlFor="engine-select">Engine:</label>
                  <select
                    id="engine-select"
                    className="bq-select"
                    value={selectedEngine}
                    onChange={(e) => setSelectedEngine(e.target.value)}
                    disabled={isExecuting}
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
                  disabled={isExecuting}
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
                  disabled={isExecuting || !queryText.trim()}
                >
                  {isExecuting ? (
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
              value={queryText}
              onChange={setQueryText}
              onExecute={executeQuery}
              disabled={isExecuting}
            />
          </div>
          
          <ResultsPanel
            results={queryResults}
            queryPlan={queryPlan}
            error={queryError}
            isLoading={isExecuting}
            currentJob={currentJob}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
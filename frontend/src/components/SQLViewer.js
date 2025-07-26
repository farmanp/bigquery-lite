import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const SQLViewer = ({ apiBaseUrl, schemaName, engine, onClose, onExecuteSQL }) => {
  const [sql, setSql] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchSQL = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await axios.get(`${apiBaseUrl}/schemas/${schemaName}/sql`, {
        params: { engine: engine }
      });

      setSql(response.data.sql || '');
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to generate ${engine} SQL`);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, schemaName, engine]);

  useEffect(() => {
    fetchSQL();
  }, [fetchSQL]);

  const handleCopySQL = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy SQL:', err);
    }
  };

  const handleExecuteSQL = () => {
    onExecuteSQL?.(sql, engine);
    onClose?.();
  };

  const getEngineIcon = (engine) => {
    switch (engine) {
      case 'duckdb':
        return 'storage';
      case 'clickhouse':
        return 'speed';
      default:
        return 'database';
    }
  };

  const getEngineColor = (engine) => {
    switch (engine) {
      case 'duckdb':
        return 'text-green-600';
      case 'clickhouse':
        return 'text-orange-600';
      default:
        return 'text-blue-600';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center">
            <span className={`material-icons ${getEngineColor(engine)} mr-2`}>
              {getEngineIcon(engine)}
            </span>
            <h3 className="text-lg font-medium text-gray-900">
              {engine.toUpperCase()} DDL for "{schemaName}"
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <span className="material-icons">close</span>
          </button>
        </div>

        <div className="flex-1 p-6 overflow-hidden flex flex-col">
          {loading ? (
            <div className="flex items-center justify-center flex-1">
              <div className="spinner mr-2"></div>
              <span className="text-gray-600">Generating SQL...</span>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center">
                <span className="material-icons text-red-500 mr-2">error</span>
                <span className="text-red-700">{error}</span>
              </div>
              <button 
                onClick={fetchSQL}
                className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="flex flex-col flex-1">
              {/* SQL Code Block */}
              <div className="flex-1 border border-gray-300 rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b border-gray-300 flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">
                    CREATE TABLE Statement
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleCopySQL}
                      className={`px-3 py-1 text-sm rounded flex items-center transition-colors ${
                        copied 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-white text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <span className="material-icons text-sm mr-1">
                        {copied ? 'check' : 'content_copy'}
                      </span>
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                    {onExecuteSQL && (
                      <button
                        onClick={handleExecuteSQL}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 flex items-center"
                      >
                        <span className="material-icons text-sm mr-1">play_arrow</span>
                        Execute
                      </button>
                    )}
                  </div>
                </div>
                <div className="p-4 overflow-auto flex-1 bg-gray-900 text-gray-100">
                  <pre className="text-sm font-mono whitespace-pre-wrap">{sql}</pre>
                </div>
              </div>

              {/* SQL Info */}
              <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                <div className="flex items-start">
                  <span className="material-icons text-blue-600 mr-2 mt-0.5">info</span>
                  <div className="text-sm text-blue-900">
                    <p className="font-medium mb-1">About this SQL:</p>
                    <ul className="list-disc list-inside space-y-1 text-blue-800">
                      <li>Generated for {engine.toUpperCase()} engine</li>
                      <li>Based on schema "{schemaName}"</li>
                      <li>You can copy this SQL and run it manually, or use the Execute button to run it directly</li>
                      {engine === 'clickhouse' && (
                        <li>ClickHouse-specific data types and engine settings applied</li>
                      )}
                      {engine === 'duckdb' && (
                        <li>DuckDB-compatible syntax and data types used</li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Close
          </button>
          {!loading && !error && onExecuteSQL && (
            <button
              onClick={handleExecuteSQL}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
            >
              <span className="material-icons mr-2">play_arrow</span>
              Execute in Query Editor
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SQLViewer;
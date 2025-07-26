import React, { useState } from 'react';
import axios from 'axios';

const TableCreation = ({ apiBaseUrl, schemaName, onTableCreated, onClose }) => {
  const [creating, setCreating] = useState(false);
  const [engine, setEngine] = useState('duckdb');
  const [tableName, setTableName] = useState(schemaName || '');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleCreateTable = async () => {
    if (!tableName.trim()) {
      setError('Please provide a table name');
      return;
    }

    try {
      setCreating(true);
      setError(null);
      setSuccess(null);

      const response = await axios.post(`${apiBaseUrl}/schemas/${schemaName}/create-table`, {
        table_name: tableName,
        engine: engine
      });

      setSuccess(`Table "${tableName}" created successfully in ${engine.toUpperCase()}!`);
      onTableCreated?.(response.data);
      
      // Auto-close after success
      setTimeout(() => {
        onClose?.();
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to create table in ${engine}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Create Table</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <span className="material-icons">close</span>
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Schema Info */}
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="flex items-center">
              <span className="material-icons text-blue-600 mr-2">schema</span>
              <span className="font-medium text-blue-900">Schema: {schemaName}</span>
            </div>
          </div>

          {/* Success Message */}
          {success && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center">
                <span className="material-icons text-green-500 mr-2">check_circle</span>
                <span className="text-green-700">{success}</span>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center">
                <span className="material-icons text-red-500 mr-2">error</span>
                <span className="text-red-700">{error}</span>
              </div>
            </div>
          )}

          {/* Table Name Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Table Name
            </label>
            <input
              type="text"
              value={tableName}
              onChange={(e) => setTableName(e.target.value)}
              placeholder="Enter table name"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={creating}
            />
          </div>

          {/* Engine Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Database Engine
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  value="duckdb"
                  checked={engine === 'duckdb'}
                  onChange={(e) => setEngine(e.target.value)}
                  className="mr-3"
                  disabled={creating}
                />
                <div className="flex items-center">
                  <span className="material-icons text-green-600 mr-2">storage</span>
                  <div>
                    <div className="font-medium">DuckDB</div>
                    <div className="text-sm text-gray-500">Interactive analytics engine</div>
                  </div>
                </div>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="clickhouse"
                  checked={engine === 'clickhouse'}
                  onChange={(e) => setEngine(e.target.value)}
                  className="mr-3"
                  disabled={creating}
                />
                <div className="flex items-center">
                  <span className="material-icons text-orange-600 mr-2">speed</span>
                  <div>
                    <div className="font-medium">ClickHouse</div>
                    <div className="text-sm text-gray-500">Distributed columnar engine</div>
                  </div>
                </div>
              </label>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            disabled={creating}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleCreateTable}
            disabled={creating || !tableName.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
          >
            {creating ? (
              <>
                <div className="spinner mr-2"></div>
                Creating...
              </>
            ) : (
              <>
                <span className="material-icons mr-2">add_circle</span>
                Create Table
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TableCreation;
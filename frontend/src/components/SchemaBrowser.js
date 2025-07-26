import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const SchemaBrowser = ({ apiBaseUrl, onCreateTable, onViewSQL }) => {
  const [schemas, setSchemas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedSchemas, setExpandedSchemas] = useState(new Set());

  const fetchSchemas = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${apiBaseUrl}/schemas`);
      setSchemas(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch schemas');
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    fetchSchemas();
  }, [fetchSchemas]);

  const toggleSchemaExpansion = (schemaName) => {
    const newExpanded = new Set(expandedSchemas);
    if (newExpanded.has(schemaName)) {
      newExpanded.delete(schemaName);
    } else {
      newExpanded.add(schemaName);
    }
    setExpandedSchemas(newExpanded);
  };

  const handleCreateTable = (schemaName, engine) => {
    onCreateTable?.(schemaName, engine);
  };

  const handleViewSQL = (schemaName, engine) => {
    onViewSQL?.(schemaName, engine);
  };

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        padding: '32px' 
      }}>
        <div className="spinner"></div>
        <span style={{ marginLeft: '12px', color: '#5f6368', fontSize: '14px' }}>Loading schemas...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        padding: '16px', 
        backgroundColor: '#fce8e6', 
        border: '1px solid #f28b82', 
        borderRadius: '8px' 
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className="material-icons" style={{ color: '#d93025', marginRight: '8px' }}>error</span>
          <span style={{ color: '#d93025', fontSize: '14px' }}>{error}</span>
        </div>
        <button 
          onClick={fetchSchemas}
          style={{
            marginTop: '12px',
            padding: '8px 16px',
            backgroundColor: '#d93025',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="schema-browser">
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        marginBottom: '16px' 
      }}>
        <h3 style={{ 
          margin: '0', 
          fontSize: '16px', 
          fontWeight: '500', 
          color: '#3c4043' 
        }}>Registered Schemas</h3>
        <button 
          onClick={fetchSchemas}
          style={{
            padding: '8px',
            color: '#5f6368',
            backgroundColor: 'transparent',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px'
          }}
          title="Refresh schemas"
          onMouseEnter={(e) => e.target.style.backgroundColor = '#f1f3f4'}
          onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
        >
          <span className="material-icons" style={{ fontSize: '18px' }}>refresh</span>
        </button>
      </div>

      {schemas.length === 0 ? (
        <div style={{ 
          textAlign: 'center', 
          padding: '32px 0', 
          color: '#5f6368' 
        }}>
          <span className="material-icons" style={{ 
            fontSize: '48px', 
            marginBottom: '8px', 
            display: 'block' 
          }}>schema</span>
          <p style={{ margin: '0 0 4px 0', fontSize: '16px' }}>No schemas registered yet</p>
          <p style={{ margin: '0', fontSize: '14px' }}>Upload a .proto or JSON schema to get started</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {schemas.map((schema) => (
            <div key={schema.name} style={{ 
              border: '1px solid #e8eaed', 
              borderRadius: '8px' 
            }}>
              <div 
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '12px',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s'
                }}
                onClick={() => toggleSchemaExpansion(schema.name)}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#f8f9fa'}
                onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
              >
                <span className="material-icons" style={{ color: '#5f6368', marginRight: '8px' }}>
                  {expandedSchemas.has(schema.name) ? 'expand_less' : 'expand_more'}
                </span>
                <span className="material-icons" style={{ color: '#1a73e8', marginRight: '8px' }}>schema</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: '500', color: '#3c4043', fontSize: '14px' }}>{schema.name}</div>
                  <div style={{ fontSize: '13px', color: '#5f6368' }}>
                    {schema.fields?.length || 0} fields • {schema.type} schema
                  </div>
                </div>
              </div>

              {expandedSchemas.has(schema.name) && (
                <div style={{ 
                  borderTop: '1px solid #e8eaed', 
                  backgroundColor: '#f8f9fa' 
                }}>
                  {/* Schema Fields */}
                  {schema.fields && schema.fields.length > 0 && (
                    <div style={{ 
                      padding: '12px', 
                      borderBottom: '1px solid #e8eaed' 
                    }}>
                      <h4 style={{ 
                        fontSize: '14px', 
                        fontWeight: '500', 
                        color: '#5f6368', 
                        margin: '0 0 8px 0' 
                      }}>Fields:</h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {schema.fields.map((field, index) => (
                          <div key={index} style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            fontSize: '13px' 
                          }}>
                            <span className="material-icons" style={{ 
                              fontSize: '16px', 
                              color: '#9aa0a6', 
                              marginRight: '8px' 
                            }}>
                              {field.type === 'string' ? 'text_fields' : 
                               field.type === 'integer' || field.type === 'number' ? 'numbers' :
                               field.type === 'boolean' ? 'check_box' : 'label'}
                            </span>
                            <span style={{ 
                              fontFamily: 'Consolas, Monaco, "Courier New", monospace', 
                              color: '#3c4043' 
                            }}>{field.name}</span>
                            <span style={{ 
                              marginLeft: '8px', 
                              padding: '2px 8px', 
                              backgroundColor: '#e8eaed', 
                              color: '#5f6368', 
                              borderRadius: '4px', 
                              fontSize: '12px' 
                            }}>
                              {field.type}
                            </span>
                            {field.required && (
                              <span style={{ 
                                marginLeft: '4px', 
                                color: '#d93025', 
                                fontSize: '12px' 
                              }}>*</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div style={{ padding: '12px' }}>
                    <div style={{ 
                      fontSize: '14px', 
                      fontWeight: '500', 
                      color: '#5f6368', 
                      marginBottom: '8px' 
                    }}>Create Table:</div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        onClick={() => handleCreateTable(schema.name, 'duckdb')}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#34a853',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '13px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#2e7d32'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#34a853'}
                      >
                        <span className="material-icons" style={{ fontSize: '16px', marginRight: '4px' }}>add_circle</span>
                        DuckDB
                      </button>
                      <button
                        onClick={() => handleCreateTable(schema.name, 'clickhouse')}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#ff9800',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '13px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#f57c00'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#ff9800'}
                      >
                        <span className="material-icons" style={{ fontSize: '16px', marginRight: '4px' }}>add_circle</span>
                        ClickHouse
                      </button>
                    </div>
                    
                    <div style={{ 
                      fontSize: '14px', 
                      fontWeight: '500', 
                      color: '#5f6368', 
                      marginBottom: '8px',
                      marginTop: '12px'
                    }}>View SQL:</div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        onClick={() => handleViewSQL(schema.name, 'duckdb')}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#1a73e8',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '13px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#1557b0'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#1a73e8'}
                      >
                        <span className="material-icons" style={{ fontSize: '16px', marginRight: '4px' }}>visibility</span>
                        DuckDB DDL
                      </button>
                      <button
                        onClick={() => handleViewSQL(schema.name, 'clickhouse')}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#9c27b0',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '13px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#7b1fa2'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#9c27b0'}
                      >
                        <span className="material-icons" style={{ fontSize: '16px', marginRight: '4px' }}>visibility</span>
                        ClickHouse DDL
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SchemaBrowser;
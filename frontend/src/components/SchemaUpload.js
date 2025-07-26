import React, { useState } from 'react';
import axios from 'axios';

const SchemaUpload = ({ apiBaseUrl, onSchemaUploaded }) => {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [uploadMethod, setUploadMethod] = useState('file'); // 'file' or 'text'
  const [textInput, setTextInput] = useState('');
  const [schemaName, setSchemaName] = useState('');
  const [schemaType, setSchemaType] = useState('proto');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleFileUpload = async (file) => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('schema_name', schemaName || file.name.split('.')[0]);
    formData.append('schema_type', file.name.endsWith('.proto') ? 'proto' : 'json');

    await uploadSchema(formData);
  };

  const handleTextUpload = async () => {
    if (!textInput.trim() || !schemaName.trim()) {
      setError('Please provide both schema name and content');
      return;
    }

    const formData = new FormData();
    const blob = new Blob([textInput], { type: 'text/plain' });
    formData.append('file', blob, `${schemaName}.${schemaType}`);
    formData.append('schema_name', schemaName);
    formData.append('schema_type', schemaType);

    await uploadSchema(formData);
  };

  const uploadSchema = async (formData) => {
    try {
      setUploading(true);
      setError(null);
      setSuccess(null);

      const response = await axios.post(`${apiBaseUrl}/schemas/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setSuccess(`Schema "${response.data.name}" uploaded successfully!`);
      setTextInput('');
      setSchemaName('');
      onSchemaUploaded?.(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload schema');
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      const file = files[0];
      if (file.name.endsWith('.proto') || file.name.endsWith('.json')) {
        handleFileUpload(file);
      } else {
        setError('Please upload a .proto or .json file');
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragActive(false);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  return (
    <div className="schema-upload" style={{ padding: '0' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h3 style={{ margin: '0', fontSize: '16px', fontWeight: '500', color: '#3c4043' }}>Upload Schema</h3>
        <div style={{ display: 'flex', border: '1px solid #dadce0', borderRadius: '8px' }}>
          <button
            onClick={() => setUploadMethod('file')}
            style={{
              padding: '8px 16px',
              fontSize: '14px',
              borderRadius: '8px 0 0 8px',
              border: 'none',
              backgroundColor: uploadMethod === 'file' ? '#1a73e8' : 'white',
              color: uploadMethod === 'file' ? 'white' : '#5f6368',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            File
          </button>
          <button
            onClick={() => setUploadMethod('text')}
            style={{
              padding: '8px 16px',
              fontSize: '14px',
              borderRadius: '0 8px 8px 0',
              border: 'none',
              backgroundColor: uploadMethod === 'text' ? '#1a73e8' : 'white',
              color: uploadMethod === 'text' ? 'white' : '#5f6368',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            Text
          </button>
        </div>
      </div>

      {/* Success Message */}
      {success && (
        <div style={{ 
          padding: '12px 16px', 
          backgroundColor: '#e8f5e8', 
          border: '1px solid #81c784', 
          borderRadius: '8px',
          marginBottom: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span className="material-icons" style={{ color: '#2e7d32', marginRight: '8px', fontSize: '20px' }}>check_circle</span>
            <span style={{ color: '#2e7d32', fontSize: '14px' }}>{success}</span>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div style={{ 
          padding: '12px 16px', 
          backgroundColor: '#fce8e6', 
          border: '1px solid #f28b82', 
          borderRadius: '8px',
          marginBottom: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span className="material-icons" style={{ color: '#d93025', marginRight: '8px', fontSize: '20px' }}>error</span>
            <span style={{ color: '#d93025', fontSize: '14px' }}>{error}</span>
          </div>
        </div>
      )}

      {uploadMethod === 'file' ? (
        <div>
          {/* Schema Name Input */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ 
              display: 'block', 
              fontSize: '14px', 
              fontWeight: '500', 
              color: '#5f6368', 
              marginBottom: '8px' 
            }}>
              Schema Name (optional)
            </label>
            <input
              type="text"
              value={schemaName}
              onChange={(e) => setSchemaName(e.target.value)}
              placeholder="Leave empty to use filename"
              style={{
                width: '100%',
                padding: '10px 12px',
                border: '1px solid #dadce0',
                borderRadius: '8px',
                fontSize: '14px',
                fontFamily: 'inherit',
                outline: 'none'
              }}
              onFocus={(e) => e.target.style.borderColor = '#1a73e8'}
              onBlur={(e) => e.target.style.borderColor = '#dadce0'}
            />
          </div>

          {/* File Drop Zone */}
          <div
            style={{
              border: `2px dashed ${dragActive ? '#1a73e8' : '#dadce0'}`,
              borderRadius: '8px',
              padding: '32px',
              textAlign: 'center',
              backgroundColor: dragActive ? '#f8f9fa' : 'white',
              transition: 'all 0.2s',
              cursor: 'pointer'
            }}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <span className="material-icons" style={{ 
              fontSize: '48px', 
              color: '#9aa0a6', 
              display: 'block', 
              marginBottom: '16px' 
            }}>cloud_upload</span>
            <p style={{ 
              fontSize: '16px', 
              fontWeight: '500', 
              color: '#3c4043', 
              margin: '0 0 8px 0' 
            }}>
              Drop your schema file here
            </p>
            <p style={{ 
              fontSize: '14px', 
              color: '#5f6368', 
              margin: '0 0 16px 0' 
            }}>
              Supports .proto and .json files
            </p>
            <label style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '10px 20px',
              backgroundColor: '#1a73e8',
              color: 'white',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              border: 'none',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#1557b0'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#1a73e8'}
            >
              <span className="material-icons" style={{ marginRight: '8px', fontSize: '18px' }}>folder_open</span>
              Choose File
              <input
                type="file"
                accept=".proto,.json"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
                disabled={uploading}
              />
            </label>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Schema Name and Type */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ 
                display: 'block', 
                fontSize: '14px', 
                fontWeight: '500', 
                color: '#5f6368', 
                marginBottom: '8px' 
              }}>
                Schema Name *
              </label>
              <input
                type="text"
                value={schemaName}
                onChange={(e) => setSchemaName(e.target.value)}
                placeholder="my_schema"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #dadce0',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontFamily: 'inherit',
                  outline: 'none'
                }}
                onFocus={(e) => e.target.style.borderColor = '#1a73e8'}
                onBlur={(e) => e.target.style.borderColor = '#dadce0'}
                required
              />
            </div>
            <div>
              <label style={{ 
                display: 'block', 
                fontSize: '14px', 
                fontWeight: '500', 
                color: '#5f6368', 
                marginBottom: '8px' 
              }}>
                Schema Type
              </label>
              <select
                value={schemaType}
                onChange={(e) => setSchemaType(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #dadce0',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontFamily: 'inherit',
                  outline: 'none',
                  backgroundColor: 'white'
                }}
                onFocus={(e) => e.target.style.borderColor = '#1a73e8'}
                onBlur={(e) => e.target.style.borderColor = '#dadce0'}
              >
                <option value="proto">Protocol Buffers (.proto)</option>
                <option value="json">JSON Schema (.json)</option>
              </select>
            </div>
          </div>

          {/* Text Area */}
          <div>
            <label style={{ 
              display: 'block', 
              fontSize: '14px', 
              fontWeight: '500', 
              color: '#5f6368', 
              marginBottom: '8px' 
            }}>
              Schema Content *
            </label>
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder={schemaType === 'proto' 
                ? 'syntax = "proto3";\n\nmessage User {\n  string name = 1;\n  int32 age = 2;\n}'
                : '{\n  "$schema": "http://json-schema.org/draft-07/schema#",\n  "type": "object",\n  "properties": {\n    "name": {\n      "type": "string"\n    }\n  }\n}'
              }
              rows={12}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #dadce0',
                borderRadius: '8px',
                fontSize: '13px',
                fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                outline: 'none',
                resize: 'vertical'
              }}
              onFocus={(e) => e.target.style.borderColor = '#1a73e8'}
              onBlur={(e) => e.target.style.borderColor = '#dadce0'}
              required
            />
          </div>

          {/* Upload Button */}
          <button
            onClick={handleTextUpload}
            disabled={uploading || !textInput.trim() || !schemaName.trim()}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '12px 20px',
              backgroundColor: (uploading || !textInput.trim() || !schemaName.trim()) ? '#dadce0' : '#1a73e8',
              color: 'white',
              borderRadius: '8px',
              border: 'none',
              fontSize: '14px',
              fontWeight: '500',
              cursor: (uploading || !textInput.trim() || !schemaName.trim()) ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => {
              if (!uploading && textInput.trim() && schemaName.trim()) {
                e.target.style.backgroundColor = '#1557b0';
              }
            }}
            onMouseLeave={(e) => {
              if (!uploading && textInput.trim() && schemaName.trim()) {
                e.target.style.backgroundColor = '#1a73e8';
              }
            }}
          >
            {uploading ? (
              <>
                <div className="spinner" style={{ marginRight: '8px' }}></div>
                Uploading...
              </>
            ) : (
              <>
                <span className="material-icons" style={{ marginRight: '8px', fontSize: '18px' }}>cloud_upload</span>
                Upload Schema
              </>
            )}
          </button>
        </div>
      )}

      {uploading && (
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center', 
          padding: '16px',
          marginTop: '16px'
        }}>
          <div className="spinner" style={{ marginRight: '8px' }}></div>
          <span style={{ color: '#5f6368', fontSize: '14px' }}>Processing schema...</span>
        </div>
      )}
    </div>
  );
};

export default SchemaUpload;
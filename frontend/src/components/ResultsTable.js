import React, { useMemo } from 'react';

const ResultsTable = ({ results }) => {
  const inferColumnType = (data, columnKey) => {
    // Sample a few rows to infer the type
    const sampleSize = Math.min(10, data.length);
    const sample = data.slice(0, sampleSize).map(row => row[columnKey]);
    
    let hasNumbers = 0;
    let hasStrings = 0;
    let hasDates = 0;
    let hasNulls = 0;

    sample.forEach(value => {
      if (value === null || value === undefined) {
        hasNulls++;
      } else if (typeof value === 'number') {
        hasNumbers++;
      } else if (typeof value === 'string') {
        // Check if it looks like a date
        if (isValidDate(value)) {
          hasDates++;
        } else {
          hasStrings++;
        }
      }
    });

    if (hasNumbers > hasStrings && hasNumbers > hasDates) return 'number';
    if (hasDates > 0) return 'date';
    return 'string';
  };

  const isValidDate = (value) => {
    const date = new Date(value);
    return !isNaN(date.getTime()) && value.includes('-');
  };

  const { columns, rows } = useMemo(() => {
    if (!results || !results.data || !Array.isArray(results.data) || results.data.length === 0) {
      return { columns: [], rows: [] };
    }

    // Extract columns from the first row
    const firstRow = results.data[0];
    const cols = Object.keys(firstRow).map(key => ({
      key,
      header: key,
      type: inferColumnType(results.data, key)
    }));

    return {
      columns: cols,
      rows: results.data
    };
  }, [results]);

  const formatCellValue = (value, type) => {
    if (value === null || value === undefined) {
      return <span style={{ color: '#9aa0a6', fontStyle: 'italic' }}>null</span>;
    }

    switch (type) {
      case 'number':
        if (typeof value === 'number') {
          return value.toLocaleString();
        }
        return value;
      
      case 'date':
        try {
          const date = new Date(value);
          if (!isNaN(date.getTime())) {
            return date.toLocaleString();
          }
        } catch (e) {
          // Fall through to default
        }
        return value;
      
      default:
        return String(value);
    }
  };

  const getCellStyle = (type) => {
    switch (type) {
      case 'number':
        return { textAlign: 'right' };
      case 'date':
        return { fontFamily: 'monospace', fontSize: '13px' };
      default:
        return {};
    }
  };

  if (columns.length === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#5f6368' }}>
        <span className="material-icons" style={{ fontSize: '48px', marginBottom: '16px', display: 'block' }}>
          inbox
        </span>
        <div>No data to display</div>
        <div style={{ fontSize: '14px', marginTop: '8px' }}>
          The query returned no results
        </div>
      </div>
    );
  }

  return (
    <div className="results-table-container">
      <table className="bq-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span>{column.header}</span>
                  <span 
                    className="material-icons" 
                    style={{ 
                      fontSize: '16px', 
                      color: '#9aa0a6',
                      opacity: 0.7 
                    }}
                  >
                    {column.type === 'number' ? 'tag' : 
                     column.type === 'date' ? 'schedule' : 'text_fields'}
                  </span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td 
                  key={column.key} 
                  style={getCellStyle(column.type)}
                  title={String(row[column.key] || '')} // Tooltip for long values
                >
                  {formatCellValue(row[column.key], column.type)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      
      {rows.length > 0 && (
        <div style={{ 
          padding: '12px 16px', 
          borderTop: '1px solid #e8eaed', 
          background: '#f8f9fa', 
          fontSize: '14px', 
          color: '#5f6368' 
        }}>
          Showing {rows.length.toLocaleString()} rows
          {rows.length >= 1000 && (
            <span style={{ marginLeft: '8px', color: '#ea8600' }}>
              (Results may be limited)
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default ResultsTable;
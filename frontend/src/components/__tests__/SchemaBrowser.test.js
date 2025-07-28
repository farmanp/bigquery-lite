import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import SchemaBrowser from '../SchemaBrowser';

// Mock axios
jest.mock('axios', () => ({
  get: jest.fn(),
}));

const mockAxios = require('axios');

describe('SchemaBrowser', () => {
  const defaultProps = {
    apiBaseUrl: 'http://localhost:8001',
    onCreateTable: jest.fn(),
    onViewSQL: jest.fn(),
  };

  const mockSchemas = [
    {
      schema_id: 'user_events',
      name: 'user_events',
      table_name: 'user_events',
      field_count: 5,
      database_name: 'bigquery_lite',
      total_versions: 1,
    },
    {
      schema_id: 'order_data',
      name: 'order_data', 
      table_name: 'order_data',
      field_count: 8,
      database_name: 'bigquery_lite',
      total_versions: 2,
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  describe('Loading State', () => {
    it('displays loading spinner while fetching schemas', async () => {
      mockAxios.get.mockImplementation(() => new Promise(() => {})); // Never resolves
      
      render(<SchemaBrowser {...defaultProps} />);
      
      expect(screen.getByText('Loading schemas...')).toBeInTheDocument();
      expect(document.querySelector('.spinner')).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    beforeEach(() => {
      mockAxios.get.mockResolvedValue({
        data: { schemas: mockSchemas, total: 2 }
      });
    });

    it('fetches schemas on component mount', async () => {
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(mockAxios.get).toHaveBeenCalledWith('http://localhost:8001/schemas');
      });
    });

    it('displays schemas after successful fetch', async () => {
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
        expect(screen.getByText('order_data')).toBeInTheDocument();
      });
    });

    it('shows schema metadata correctly', async () => {
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('5 fields • bigquery_lite database')).toBeInTheDocument();
        expect(screen.getByText('8 fields • bigquery_lite database')).toBeInTheDocument();
      });
    });

    it('handles direct schemas array response', async () => {
      mockAxios.get.mockResolvedValue({ data: mockSchemas });
      
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
    });
  });

  describe('Error State', () => {
    it('displays error message when fetch fails', async () => {
      const errorMessage = 'Network Error';
      mockAxios.get.mockRejectedValue({
        response: { data: { detail: errorMessage } }
      });
      
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });

    it('displays generic error for unknown errors', async () => {
      mockAxios.get.mockRejectedValue(new Error('Unknown error'));
      
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to fetch schemas')).toBeInTheDocument();
      });
    });

    it('allows retry after error', async () => {
      mockAxios.get
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ data: { schemas: mockSchemas } });
      
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to fetch schemas')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('Retry'));
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      expect(mockAxios.get).toHaveBeenCalledTimes(2);
    });
  });

  describe('Empty State', () => {
    it('displays empty state when no schemas exist', async () => {
      mockAxios.get.mockResolvedValue({ data: { schemas: [], total: 0 } });
      
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('No schemas registered yet')).toBeInTheDocument();
        expect(screen.getByText('Upload a .proto or JSON schema to get started')).toBeInTheDocument();
      });
    });
  });

  describe('Schema Expansion', () => {
    beforeEach(() => {
      mockAxios.get.mockResolvedValue({
        data: { schemas: mockSchemas }
      });
    });

    it('expands schema details when clicked', async () => {
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      // Click to expand - get the first occurrence (the header)
      const schemaHeader = screen.getAllByText('user_events')[0];
      fireEvent.click(schemaHeader);
      
      await waitFor(() => {
        expect(screen.getByText('Schema ID:')).toBeInTheDocument();
        expect(screen.getByText('Field Count:')).toBeInTheDocument();
        expect(screen.getByText('Total Versions:')).toBeInTheDocument();
      });
    });

    it('collapses schema when clicked again', async () => {
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      // Find the clickable schema header (not the expanded one)
      const schemaHeaders = screen.getAllByText('user_events');
      const clickableHeader = schemaHeaders[0]; // First one is the clickable header
      
      // Expand
      fireEvent.click(clickableHeader);
      
      await waitFor(() => {
        expect(screen.getByText('Schema ID:')).toBeInTheDocument();
      });
      
      // Collapse - click the same header again
      fireEvent.click(clickableHeader);
      
      await waitFor(() => {
        expect(screen.queryByText('Schema ID:')).not.toBeInTheDocument();
      });
    });

    it('shows create table buttons when expanded', async () => {
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      const schemaHeader = screen.getAllByText('user_events')[0];
      fireEvent.click(schemaHeader);
      
      await waitFor(() => {
        expect(screen.getByText('DuckDB')).toBeInTheDocument();
        expect(screen.getByText('ClickHouse')).toBeInTheDocument();
      });
    });

    it('shows view SQL buttons when expanded', async () => {
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      const schemaHeader = screen.getAllByText('user_events')[0];
      fireEvent.click(schemaHeader);
      
      await waitFor(() => {
        expect(screen.getByText('DuckDB DDL')).toBeInTheDocument();
        expect(screen.getByText('ClickHouse DDL')).toBeInTheDocument();
      });
    });
  });

  describe('Button Interactions', () => {
    beforeEach(() => {
      mockAxios.get.mockResolvedValue({
        data: { schemas: mockSchemas }
      });
    });

    it('calls onCreateTable when DuckDB create button clicked', async () => {
      const mockOnCreateTable = jest.fn();
      render(<SchemaBrowser {...defaultProps} onCreateTable={mockOnCreateTable} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      const schemaHeader = screen.getAllByText('user_events')[0];
      fireEvent.click(schemaHeader);
      
      await waitFor(() => {
        expect(screen.getByText('DuckDB')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('DuckDB'));
      
      expect(mockOnCreateTable).toHaveBeenCalledWith('user_events', 'duckdb');
    });

    it('calls onCreateTable when ClickHouse create button clicked', async () => {
      const mockOnCreateTable = jest.fn();
      render(<SchemaBrowser {...defaultProps} onCreateTable={mockOnCreateTable} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      const schemaHeader = screen.getAllByText('user_events')[0];
      fireEvent.click(schemaHeader);
      
      await waitFor(() => {
        expect(screen.getByText('ClickHouse')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('ClickHouse'));
      
      expect(mockOnCreateTable).toHaveBeenCalledWith('user_events', 'clickhouse');
    });

    it('calls onViewSQL when DuckDB DDL button clicked', async () => {
      const mockOnViewSQL = jest.fn();
      render(<SchemaBrowser {...defaultProps} onViewSQL={mockOnViewSQL} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      const schemaHeader = screen.getAllByText('user_events')[0];
      fireEvent.click(schemaHeader);
      
      await waitFor(() => {
        expect(screen.getByText('DuckDB DDL')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('DuckDB DDL'));
      
      expect(mockOnViewSQL).toHaveBeenCalledWith('user_events', 'duckdb');
    });

    it('calls onViewSQL when ClickHouse DDL button clicked', async () => {
      const mockOnViewSQL = jest.fn();
      render(<SchemaBrowser {...defaultProps} onViewSQL={mockOnViewSQL} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      const schemaHeader = screen.getAllByText('user_events')[0];
      fireEvent.click(schemaHeader);
      
      await waitFor(() => {
        expect(screen.getByText('ClickHouse DDL')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('ClickHouse DDL'));
      
      expect(mockOnViewSQL).toHaveBeenCalledWith('user_events', 'clickhouse');
    });
  });

  describe('Refresh Functionality', () => {
    beforeEach(() => {
      mockAxios.get.mockResolvedValue({
        data: { schemas: mockSchemas }
      });
    });

    it('refetches schemas when refresh button clicked', async () => {
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      expect(mockAxios.get).toHaveBeenCalledTimes(1);
      
      fireEvent.click(screen.getByTitle('Refresh schemas'));
      
      await waitFor(() => {
        expect(mockAxios.get).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles schemas without schema_id', async () => {
      const schemasWithoutId = [
        {
          name: 'schema_without_id',
          table_name: 'schema_without_id',
          field_count: 3,
        }
      ];
      
      mockAxios.get.mockResolvedValue({
        data: { schemas: schemasWithoutId }
      });
      
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('schema_without_id')).toBeInTheDocument();
      });
    });

    it('handles missing optional callback props', async () => {
      mockAxios.get.mockResolvedValue({
        data: { schemas: mockSchemas }
      });
      
      render(<SchemaBrowser apiBaseUrl="http://localhost:8001" />);
      
      await waitFor(() => {
        expect(screen.getByText('user_events')).toBeInTheDocument();
      });
      
      const schemaHeader = screen.getAllByText('user_events')[0];
      fireEvent.click(schemaHeader);
      
      await waitFor(() => {
        expect(screen.getByText('DuckDB')).toBeInTheDocument();
      });
      
      // Should not crash when clicking buttons without callbacks
      expect(() => {
        fireEvent.click(screen.getByText('DuckDB'));
      }).not.toThrow();
    });

    it('handles non-array response gracefully', async () => {
      mockAxios.get.mockResolvedValue({
        data: { schemas: 'not an array' }
      });
      
      render(<SchemaBrowser {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('No schemas registered yet')).toBeInTheDocument();
      });
    });
  });
});
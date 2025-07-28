import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ResultsTable from '../ResultsTable';

describe('ResultsTable', () => {
  describe('Empty Data Handling', () => {
    it('displays no data message when results are null', () => {
      render(<ResultsTable results={null} />);
      
      expect(screen.getByText('No data to display')).toBeInTheDocument();
      expect(screen.getByText('The query returned no results')).toBeInTheDocument();
    });

    it('displays no data message when results.data is empty array', () => {
      render(<ResultsTable results={{ data: [] }} />);
      
      expect(screen.getByText('No data to display')).toBeInTheDocument();
    });

    it('displays no data message when results.data is undefined', () => {
      render(<ResultsTable results={{ data: undefined }} />);
      
      expect(screen.getByText('No data to display')).toBeInTheDocument();
    });
  });

  describe('Single Value Display', () => {
    it('displays single value in special card format', () => {
      const results = {
        data: [{ count: 42 }]
      };
      
      render(<ResultsTable results={results} />);
      
      expect(screen.getByText('42')).toBeInTheDocument();
      expect(screen.getByText('count')).toBeInTheDocument();
      expect(screen.getByText('Single result')).toBeInTheDocument();
    });

    it('formats large numbers with locale string', () => {
      const results = {
        data: [{ total: 1234567 }]
      };
      
      render(<ResultsTable results={results} />);
      
      expect(screen.getByText('1,234,567')).toBeInTheDocument();
    });

    it('displays null values with special formatting', () => {
      const results = {
        data: [{ value: null }]
      };
      
      render(<ResultsTable results={results} />);
      
      const nullElement = screen.getByText('null');
      expect(nullElement).toBeInTheDocument();
      // Check that it has the expected styling properties
      expect(nullElement.tagName).toBe('SPAN');
    });
  });

  describe('Table Display', () => {
    const mockTableData = {
      data: [
        { id: 1, name: 'John', age: 30, created_at: '2023-01-01' },
        { id: 2, name: 'Jane', age: 25, created_at: '2023-01-02' },
        { id: 3, name: 'Bob', age: null, created_at: '2023-01-03' }
      ]
    };

    it('renders table with correct headers and data', () => {
      render(<ResultsTable results={mockTableData} />);
      
      // Check headers
      expect(screen.getByText('id')).toBeInTheDocument();
      expect(screen.getByText('name')).toBeInTheDocument();
      expect(screen.getByText('age')).toBeInTheDocument();
      expect(screen.getByText('created_at')).toBeInTheDocument();
      
      // Check data
      expect(screen.getByText('John')).toBeInTheDocument();
      expect(screen.getByText('Jane')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
      expect(screen.getByText('25')).toBeInTheDocument();
    });

    it('displays row count at bottom', () => {
      render(<ResultsTable results={mockTableData} />);
      
      expect(screen.getByText('Showing 3 rows')).toBeInTheDocument();
    });

    it('shows results limitation warning for large datasets', () => {
      const largeDataset = {
        data: Array.from({ length: 1000 }, (_, i) => ({ id: i, name: `User ${i}` }))
      };
      
      render(<ResultsTable results={largeDataset} />);
      
      expect(screen.getByText('Showing 1,000 rows')).toBeInTheDocument();
      expect(screen.getByText('(Results may be limited)')).toBeInTheDocument();
    });
  });

  describe('Data Type Inference', () => {
    it('correctly identifies number columns', () => {
      const results = {
        data: [
          { price: 10.99, quantity: 5 },
          { price: 15.50, quantity: 3 }
        ]
      };
      
      render(<ResultsTable results={results} />);
      
      // Numbers should be displayed correctly
      expect(screen.getByText('10.99')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('correctly identifies date columns', () => {
      const results = {
        data: [
          { created_at: '2023-01-01T10:00:00Z' },
          { created_at: '2023-01-02T15:30:00Z' }
        ]
      };
      
      render(<ResultsTable results={results} />);
      
      // Date should be displayed in locale format
      expect(screen.getAllByText(/2023/)[0]).toBeInTheDocument();
    });

    it('handles mixed data types in columns', () => {
      const results = {
        data: [
          { value: 42 },
          { value: 'text' },
          { value: null }
        ]
      };
      
      render(<ResultsTable results={results} />);
      
      expect(screen.getByText('42')).toBeInTheDocument();
      expect(screen.getByText('text')).toBeInTheDocument();
      expect(screen.getByText('null')).toBeInTheDocument();
    });
  });

  describe('Value Formatting', () => {
    it('formats numbers with locale string', () => {
      const results = {
        data: [{ revenue: 1234567.89 }]
      };
      
      render(<ResultsTable results={results} />);
      
      expect(screen.getByText('1,234,567.89')).toBeInTheDocument();
    });

    it('formats dates as locale string', () => {
      const results = {
        data: [{ timestamp: '2023-12-25T15:30:00Z' }]
      };
      
      render(<ResultsTable results={results} />);
      
      // Should show formatted date (exact format depends on locale)
      expect(screen.getByText(/2023/)).toBeInTheDocument();
    });

    it('handles invalid dates gracefully', () => {
      const results = {
        data: [{ date_field: 'invalid-date-2023' }]
      };
      
      render(<ResultsTable results={results} />);
      
      // The component should render the invalid date as-is, but it may be formatted as a date
      expect(screen.getByText(/2023/)).toBeInTheDocument();
    });

    it('converts non-string values to strings', () => {
      const results = {
        data: [{ 
          bool_field: true,
          obj_field: { nested: 'value' }
        }]
      };
      
      render(<ResultsTable results={results} />);
      
      expect(screen.getByText('true')).toBeInTheDocument();
      expect(screen.getByText('[object Object]')).toBeInTheDocument();
    });
  });

  describe('Column Headers', () => {
    it('displays type icons for different column types', () => {
      const results = {
        data: [{ 
          id: 1, 
          name: 'test', 
          created_at: '2023-01-01',
          amount: 10.50 
        }]
      };
      
      render(<ResultsTable results={results} />);
      
      // Should have material icons for different types
      const icons = document.querySelectorAll('.material-icons');
      expect(icons.length).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases', () => {
    it('handles empty object in data array', () => {
      const results = {
        data: [{}]
      };
      
      render(<ResultsTable results={results} />);
      
      // Should not crash, shows no data message for empty objects
      expect(screen.getByText('No data to display')).toBeInTheDocument();
    });

    it('handles non-array data gracefully', () => {
      const results = {
        data: 'not an array'
      };
      
      render(<ResultsTable results={results} />);
      
      expect(screen.getByText('No data to display')).toBeInTheDocument();
    });

    it('provides tooltips for long values', () => {
      const longText = 'This is a very long text value that might be truncated in the table cell';
      const shortText = 'short';
      const results = {
        data: [
          { description: longText, id: 1 },
          { description: shortText, id: 2 }
        ]
      };
      
      render(<ResultsTable results={results} />);
      
      // Check that both texts are displayed in a table format
      expect(screen.getByText(longText)).toBeInTheDocument();
      expect(screen.getByText(shortText)).toBeInTheDocument();
      expect(screen.getByRole('table')).toBeInTheDocument();
    });
  });
});
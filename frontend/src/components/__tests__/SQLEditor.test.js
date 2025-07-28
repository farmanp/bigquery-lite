import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import SQLEditor from '../SQLEditor';

// Mock Monaco Editor
const mockSetMonarchTokensProvider = jest.fn();
const mockAddCommand = jest.fn();
const mockAddAction = jest.fn();

jest.mock('@monaco-editor/react', () => {
  const mockReact = require('react');
  
  return {
    __esModule: true,
    default: ({ value, onChange, onMount, options }) => {
      const mockEditor = {
        addCommand: mockAddCommand,
        addAction: mockAddAction,
      };
      
      mockReact.useEffect(() => {
        if (onMount) {
          const mockMonaco = {
            KeyMod: { CtrlCmd: 1 },
            KeyCode: { Enter: 2 },
            languages: {
              setMonarchTokensProvider: mockSetMonarchTokensProvider,
            },
          };
          onMount(mockEditor, mockMonaco);
        }
      }, [onMount]);

      return mockReact.createElement('textarea', {
        'data-testid': 'mock-monaco-editor',
        value: value || '',
        onChange: (e) => {
          if (onChange && typeof onChange === 'function') {
            // Monaco Editor calls onChange with the value directly, not an event
            onChange(e.target.value);
          }
        },
        readOnly: options?.readOnly,
        placeholder: 'SQL Editor'
      });
    },
  };
});

describe('SQLEditor', () => {
  const defaultProps = {
    value: '',
    onChange: jest.fn(),
    onExecute: jest.fn(),
    disabled: false,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockSetMonarchTokensProvider.mockClear();
    mockAddCommand.mockClear();
    mockAddAction.mockClear();
  });

  it('renders the editor container', () => {
    render(<SQLEditor {...defaultProps} />);
    expect(screen.getByTestId('mock-monaco-editor')).toBeInTheDocument();
  });

  it('displays the provided value', () => {
    const testValue = 'SELECT * FROM users';
    render(<SQLEditor {...defaultProps} value={testValue} />);
    
    const editor = screen.getByTestId('mock-monaco-editor');
    expect(editor).toHaveValue(testValue);
  });

  it('calls onChange when editor content changes', () => {
    const mockOnChange = jest.fn();
    render(<SQLEditor {...defaultProps} onChange={mockOnChange} />);
    
    const editor = screen.getByTestId('mock-monaco-editor');
    fireEvent.change(editor, { target: { value: 'SELECT 1' } });
    
    expect(mockOnChange).toHaveBeenCalledWith('SELECT 1');
  });

  it('handles empty value correctly', () => {
    const mockOnChange = jest.fn();
    const { rerender } = render(<SQLEditor {...defaultProps} onChange={mockOnChange} />);
    
    // Test by re-rendering with empty value
    rerender(<SQLEditor {...defaultProps} onChange={mockOnChange} value="" />);
    
    const editor = screen.getByTestId('mock-monaco-editor');
    expect(editor).toHaveValue('');
  });

  it('sets readOnly when disabled', () => {
    render(<SQLEditor {...defaultProps} disabled={true} />);
    
    const editor = screen.getByTestId('mock-monaco-editor');
    expect(editor).toHaveAttribute('readOnly');
  });

  it('does not set readOnly when enabled', () => {
    render(<SQLEditor {...defaultProps} disabled={false} />);
    
    const editor = screen.getByTestId('mock-monaco-editor');
    expect(editor).not.toHaveAttribute('readOnly');
  });

  it('configures Monaco editor on mount', async () => {
    const mockOnExecute = jest.fn();
    render(<SQLEditor {...defaultProps} onExecute={mockOnExecute} />);
    
    // Wait for the editor to mount and configure
    await waitFor(() => {
      expect(screen.getByTestId('mock-monaco-editor')).toBeInTheDocument();
    });
  });

  describe('Editor Configuration', () => {
    it('should configure SQL language tokenizer', () => {
      render(<SQLEditor {...defaultProps} />);
      
      expect(mockSetMonarchTokensProvider).toHaveBeenCalledWith(
        'sql',
        expect.objectContaining({
          keywords: expect.arrayContaining(['SELECT', 'FROM', 'WHERE']),
          operators: expect.arrayContaining(['=', '>', '<']),
        })
      );
    });
  });

  describe('Edge Cases', () => {
    it('handles null onChange gracefully', () => {
      render(<SQLEditor {...defaultProps} onChange={null} />);
      
      const editor = screen.getByTestId('mock-monaco-editor');
      fireEvent.change(editor, { target: { value: 'SELECT 1' } });
      // Should not crash, even though onChange is null
      expect(editor).toBeInTheDocument();
    });

    it('handles undefined value', () => {
      render(<SQLEditor {...defaultProps} value={undefined} />);
      
      const editor = screen.getByTestId('mock-monaco-editor');
      expect(editor).toHaveValue('');
    });
  });
});
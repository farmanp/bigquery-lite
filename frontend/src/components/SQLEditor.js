import React, { useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';

const SQLEditor = ({ value, onChange, onExecute, disabled }) => {
  const editorRef = useRef(null);

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
    
    // Configure SQL language features
    monaco.languages.setMonarchTokensProvider('sql', {
      defaultToken: '',
      tokenPostfix: '.sql',
      ignoreCase: true,
      
      brackets: [
        { open: '[', close: ']', token: 'delimiter.square' },
        { open: '(', close: ')', token: 'delimiter.parenthesis' }
      ],
      
      keywords: [
        'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT',
        'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'TABLE',
        'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON', 'AS', 'AND', 'OR',
        'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL', 'DISTINCT',
        'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'CASE', 'WHEN', 'THEN', 'ELSE',
        'END', 'UNION', 'ALL', 'WITH', 'RECURSIVE', 'CAST', 'EXTRACT',
        'DATE', 'TIMESTAMP', 'INTERVAL', 'OVER', 'PARTITION', 'WINDOW',
        'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'LAG', 'LEAD', 'FIRST_VALUE',
        'LAST_VALUE', 'PERCENTILE_CONT', 'STDDEV', 'VARIANCE'
      ],
      
      operators: [
        '=', '>', '<', '!', '~', '?', ':', '==', '<=', '>=', '!=',
        '&&', '||', '++', '--', '+', '-', '*', '/', '&', '|', '^', '%',
        '<<', '>>', '>>>', '+=', '-=', '*=', '/=', '&=', '|=', '^=',
        '%=', '<<=', '>>=', '>>>='
      ],
      
      symbols: /[=><!~?:&|+\-*\/\^%]+/,
      
      tokenizer: {
        root: [
          [/[a-z_$][\w$]*/, {
            cases: {
              '@keywords': 'keyword',
              '@default': 'identifier'
            }
          }],
          [/[A-Z][\w\$]*/, {
            cases: {
              '@keywords': 'keyword',
              '@default': 'identifier'
            }
          }],
          
          { include: '@whitespace' },
          [/[{}()\[\]]/, '@brackets'],
          [/[<>](?!@symbols)/, '@brackets'],
          [/@symbols/, {
            cases: {
              '@operators': 'delimiter',
              '@default': ''
            }
          }],
          
          [/\d*\.\d+([eE][\-+]?\d+)?/, 'number.float'],
          [/0[xX][0-9a-fA-F]+/, 'number.hex'],
          [/\d+/, 'number'],
          
          [/[;,.]/, 'delimiter'],
          
          [/'([^'\\]|\\.)*$/, 'string.invalid'],
          [/'/, 'string', '@string'],
          [/"([^"\\]|\\.)*$/, 'string.invalid'],
          [/"/, 'string', '@string_double'],
        ],
        
        string: [
          [/[^\\']+/, 'string'],
          [/\\./, 'string.escape.invalid'],
          [/'/, 'string', '@pop']
        ],
        
        string_double: [
          [/[^\\"]+/, 'string'],
          [/\\./, 'string.escape.invalid'],
          [/"/, 'string', '@pop']
        ],
        
        whitespace: [
          [/[ \t\r\n]+/, 'white'],
          [/--.*$/, 'comment'],
          [/\/\*/, 'comment', '@comment']
        ],
        
        comment: [
          [/[^\/*]+/, 'comment'],
          [/\/\*/, 'comment', '@push'],
          [/\*\//, 'comment', '@pop'],
          [/[\/*]/, 'comment']
        ]
      }
    });

    // Add keyboard shortcuts
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      if (!disabled) {
        onExecute();
      }
    });

    // Add command palette action
    editor.addAction({
      id: 'run-query',
      label: 'Run Query',
      keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter],
      contextMenuGroupId: 'navigation',
      contextMenuOrder: 1.5,
      run: () => {
        if (!disabled) {
          onExecute();
        }
      }
    });
  };

  const handleEditorChange = (newValue) => {
    if (onChange && typeof onChange === 'function') {
      onChange(newValue || '');
    }
  };

  return (
    <div className="editor-container">
      <Editor
        height="300px"
        defaultLanguage="sql"
        value={value}
        onChange={handleEditorChange}
        onMount={handleEditorDidMount}
        options={{
          theme: 'vs',
          fontSize: 14,
          lineNumbers: 'on',
          roundedSelection: false,
          scrollBeyondLastLine: false,
          readOnly: disabled,
          minimap: { enabled: false },
          automaticLayout: true,
          wordWrap: 'on',
          lineDecorationsWidth: 10,
          lineNumbersMinChars: 3,
          glyphMargin: false,
          folding: true,
          renderLineHighlight: 'all',
          selectOnLineNumbers: true,
          scrollbar: {
            vertical: 'visible',
            horizontal: 'visible',
            useShadows: false,
            verticalHasArrows: false,
            horizontalHasArrows: false
          },
          suggestOnTriggerCharacters: true,
          acceptSuggestionOnEnter: 'on',
          tabCompletion: 'on',
          quickSuggestions: true,
          parameterHints: {
            enabled: true
          }
        }}
      />
    </div>
  );
};

export default SQLEditor;
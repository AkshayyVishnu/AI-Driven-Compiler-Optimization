import { useRef, useState, useEffect } from 'react'
import Editor from '@monaco-editor/react'
import { FileCode, Trash2, Copy, Check } from 'lucide-react'

const LANGUAGES = [
  { value: 'cpp',    label: 'C++',    monaco: 'cpp'        },
  { value: 'c',      label: 'C',      monaco: 'c'          },
  { value: 'python', label: 'Python', monaco: 'python'     },
  { value: 'java',   label: 'Java',   monaco: 'java'       },
  { value: 'go',     label: 'Go',     monaco: 'go'         },
]

const MONACO_LIGHT_THEME = {
  base: 'vs',
  inherit: true,
  rules: [
    { token: 'comment',    foreground: '6B7280', fontStyle: 'italic' },
    { token: 'keyword',    foreground: '2563EB', fontStyle: 'bold'   },
    { token: 'string',     foreground: '16A34A'                       },
    { token: 'number',     foreground: 'D97706'                       },
    { token: 'type',       foreground: '7C3AED'                       },
    { token: 'function',   foreground: '0891B2'                       },
    { token: 'identifier', foreground: '1E293B'                       },
  ],
  colors: {
    'editor.background':           '#FAFBFF',
    'editor.foreground':           '#1E293B',
    'editorLineNumber.foreground': '#CBD5E1',
    'editorLineNumber.activeForeground': '#2563EB',
    'editor.lineHighlightBackground': '#EEF2FF',
    'editor.selectionBackground':  '#DBEAFE',
    'editorCursor.foreground':     '#2563EB',
    'editorIndentGuide.background':'#E2E8F0',
    'editorIndentGuide.activeBackground': '#93C5FD',
    'scrollbarSlider.background':  '#D1D9F0',
    'scrollbarSlider.hoverBackground': '#93C5FD',
  },
}

const MONACO_DARK_THEME = {
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: 'comment',    foreground: '475569', fontStyle: 'italic' },
    { token: 'keyword',    foreground: '60A5FA', fontStyle: 'bold'   },
    { token: 'string',     foreground: '4ADE80'                       },
    { token: 'number',     foreground: 'FCD34D'                       },
    { token: 'type',       foreground: 'A78BFA'                       },
    { token: 'function',   foreground: '22D3EE'                       },
    { token: 'identifier', foreground: 'E2E8F6'                       },
  ],
  colors: {
    'editor.background':           '#0C1220',
    'editor.foreground':           '#E2E8F6',
    'editorLineNumber.foreground': '#1E2D4A',
    'editorLineNumber.activeForeground': '#3B82F6',
    'editor.lineHighlightBackground': '#111929',
    'editor.selectionBackground':  '#1E3A5F',
    'editorCursor.foreground':     '#3B82F6',
    'editorIndentGuide.background':'#1E2D4A',
    'editorIndentGuide.activeBackground': '#1D4ED8',
    'scrollbarSlider.background':  '#1E2D4A',
    'scrollbarSlider.hoverBackground': '#1D4ED8',
  },
}

export default function CodeEditor({
  code, setCode, language, setLanguage, theme,
  allErrors = [],
  fixedErrors = new Set(),
  onGutterClick,
  onEditorMount,
}) {
  const editorRef             = useRef(null)
  const monacoRef             = useRef(null)
  const decorationsRef        = useRef(null)
  const lineHighlightDecRef   = useRef(null)
  const [copied, setCopied]   = useState(false)

  // Keep a stable ref so the onMouseDown closure always reads the latest errors
  const findingsRef = useRef(allErrors)
  useEffect(() => { findingsRef.current = allErrors }, [allErrors])

  const monacoLang = LANGUAGES.find(l => l.value === language)?.monaco ?? 'cpp'
  const monacoThemeName = theme === 'dark' ? 'compiler-dark' : 'compiler-light'

  // ── Sync decorations whenever errors or fixedErrors change ────────────────
  useEffect(() => {
    const editor = editorRef.current
    const monaco = monacoRef.current
    if (!editor || !monaco) return

    const model = editor.getModel()
    if (!model) return

    const errKey  = f => `${f.type}:${f.line}`
    const unfixed = allErrors.filter(f => !fixedErrors.has(errKey(f)))

    // 1. Squiggly markers — only for unfixed errors; fixed lines get no red squiggle
    const markers = unfixed.map(f => ({
      startLineNumber: f.line ?? 1,
      startColumn:     f.col_start ?? 1,
      endLineNumber:   f.line ?? 1,
      endColumn:       Math.max((f.col_start ?? 1) + 1, f.col_end ?? (f.col_start ?? 1) + 8),
      message:         `[${(f.severity ?? 'info').toUpperCase()}] ${(f.type ?? '').replace(/_/g, ' ')}: ${f.description}`,
      severity:        f.severity === 'high'   ? monaco.MarkerSeverity.Error
                     : f.severity === 'medium' ? monaco.MarkerSeverity.Warning
                     :                           monaco.MarkerSeverity.Info,
      source:          'error-scan',
    }))
    monaco.editor.setModelMarkers(model, 'error-scan', markers)

    // 2. Gutter glyphs — only for unfixed errors
    if (decorationsRef.current) decorationsRef.current.clear()
    // 3. Full-line highlights — red for unfixed, green for fixed, nothing for clean lines
    if (lineHighlightDecRef.current) lineHighlightDecRef.current.clear()

    const glyphDecorations = unfixed.map(f => ({
      range: new monaco.Range(f.line ?? 1, 1, f.line ?? 1, 1),
      options: {
        glyphMarginClassName: `security-glyph-${f.severity ?? 'low'}`,
        glyphMarginHoverMessage: {
          value: `**${(f.severity ?? 'info').toUpperCase()}** ${(f.type ?? '').replace(/_/g, ' ')} — click for details`,
        },
        isWholeLine: false,
      },
    }))

    const lineDecorations = [
      // Red highlight only for unfixed errors — fixed lines get no decoration at all
      ...unfixed.map(f => ({
        range: new monaco.Range(f.line ?? 1, 1, f.line ?? 1, 1),
        options: {
          isWholeLine: true,
          className:   'error-line-unfixed',
          overviewRuler: {
            color:    'rgba(220,38,38,0.6)',
            position: monaco.editor.OverviewRulerLane.Right,
          },
        },
      })),
      // fixed array intentionally produces no decorations — line returns to normal
    ]

    if (glyphDecorations.length > 0) {
      decorationsRef.current = editor.createDecorationsCollection(glyphDecorations)
    }
    if (lineDecorations.length > 0) {
      lineHighlightDecRef.current = editor.createDecorationsCollection(lineDecorations)
    }
  }, [allErrors, fixedErrors])

  function handleEditorMount(editor, monaco) {
    editorRef.current  = editor
    monacoRef.current  = monaco

    monaco.editor.defineTheme('compiler-light', MONACO_LIGHT_THEME)
    monaco.editor.defineTheme('compiler-dark',  MONACO_DARK_THEME)
    monaco.editor.setTheme(monacoThemeName)

    // Expose editor + monaco instance to parent for imperative fixes
    onEditorMount?.(editor, monaco)

    // Gutter click detection
    editor.onMouseDown((e) => {
      if (
        e.target.type === monaco.editor.MouseTargetType.GUTTER_GLYPH_MARGIN &&
        onGutterClick
      ) {
        const line    = e.target.position?.lineNumber
        const finding = findingsRef.current.find(f => f.line === line)
        if (finding) {
          const domNode  = editor.getDomNode()
          if (!domNode) return
          const rect     = domNode.getBoundingClientRect()
          const scrolled = editor.getScrolledVisiblePosition(e.target.position)
          if (scrolled) {
            onGutterClick(finding, {
              x: rect.left + scrolled.left + 28,
              y: rect.top  + scrolled.top,
            })
          }
        }
      }
    })
  }

  function handleEditorWillMount(monaco) {
    monacoRef.current = monaco
    monaco.editor.defineTheme('compiler-light', MONACO_LIGHT_THEME)
    monaco.editor.defineTheme('compiler-dark',  MONACO_DARK_THEME)
  }

  function handleCopy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }

  function handleClear() {
    setCode('')
    editorRef.current?.focus()
  }

  return (
    <>
      <div className="pane-header">
        <FileCode size={14} strokeWidth={2} style={{ color: 'var(--primary)' }} />
        <span className="pane-title">Source Code</span>

        <div className="pane-actions">
          {/* Language selector */}
          <select
            className="lang-select"
            value={language}
            onChange={e => setLanguage(e.target.value)}
            aria-label="Select language"
          >
            {LANGUAGES.map(l => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>

          {/* Copy */}
          <button className="icon-btn" onClick={handleCopy} title="Copy code">
            {copied ? <Check size={13} strokeWidth={2.5} style={{ color: 'var(--accent-green)' }} /> : <Copy size={13} strokeWidth={2} />}
          </button>

          {/* Clear */}
          <button className="icon-btn" onClick={handleClear} title="Clear editor">
            <Trash2 size={13} strokeWidth={2} />
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Editor
          height="100%"
          language={monacoLang}
          value={code}
          onChange={val => setCode(val ?? '')}
          theme={monacoThemeName}
          beforeMount={handleEditorWillMount}
          onMount={handleEditorMount}
          options={{
            glyphMargin:          true,
            fontSize:             13,
            fontFamily:           "'JetBrains Mono', 'Fira Code', monospace",
            fontLigatures:        true,
            lineHeight:           1.7,
            minimap:              { enabled: true, scale: 0.8 },
            scrollBeyondLastLine: false,
            wordWrap:             'on',
            padding:              { top: 14, bottom: 14 },
            renderLineHighlight:  'line',
            smoothScrolling:      true,
            cursorBlinking:       'smooth',
            cursorSmoothCaretAnimation: 'on',
            bracketPairColorization: { enabled: true },
            guides: {
              bracketPairs: true,
              indentation:  true,
            },
            suggest: { showWords: true },
            renderWhitespace: 'selection',
            roundedSelection: true,
            scrollbar: {
              verticalScrollbarSize:   8,
              horizontalScrollbarSize: 8,
            },
          }}
        />
      </div>
    </>
  )
}

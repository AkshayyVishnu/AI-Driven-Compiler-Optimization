import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import Header from './components/Header'
import CodeEditor from './components/CodeEditor'
import OutputTerminal from './components/OutputTerminal'
import ResultsPanel from './components/ResultsPanel'
import SecurityTooltip from './components/SecurityTooltip'
import SecurityFixPreviewModal from './components/SecurityFixPreviewModal'
import SustainabilityDashboard from './components/SustainabilityDashboard'
import './index.css'
import { runSyntaxCheck } from './utils/syntaxCheck'
import { applyRuleFix } from './utils/ruleFixes'

const DEFAULT_CODE = `#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// DeepCompile Security Demo
// Click "Scan Security" to find issues, then "Fix All" to auto-patch them.

/* ============================================================
   SECTION A — Auto-fixable by the optimiser (rule-based fixes)
   ============================================================ */

/* A1. Hardcoded credentials (CWE-798) */
const char* password = "hunter2secret";
const char* api_key  = "sk-live-abc123xyz";

/* A2. Global uninitialized variable */
int globalCounter;

/* A3. Unsafe string functions (CWE-676) */
void greet_user(char* username) {
    char buf[64];
    gets(buf);                            // unsafe gets       -> fgets()

    char name[32];
    strcpy(name, username);               // buffer overflow   -> strncpy()

    char greeting[128];
    sprintf(greeting, "Hello %s!", name); // unsafe sprintf   -> snprintf()

    char log_line[256];
    strcat(log_line, greeting);           // unsafe strcat     -> strncat()

    printf(username);                     // format string bug -> printf("%s", ...)
}

/* A4. Unsafe input (CWE-134) */
void read_input(char* dest) {
    scanf("%s", dest);                    // unbounded scanf   -> scanf("%127s", ...)
}

/* A5. Uninitialized locals + off-by-one + memory leak */
int compute_stats(int n) {
    int result;                           // uninitialized     -> int result = 0;
    int* data = (int*)malloc(n * sizeof(int)); // memory leak  -> ensure free()

    for (int i = 0; i <= n; i++) {        // off-by-one        -> i < n
        data[i] = i * 2;
    }

    if (result > 0) {
        printf("Stats: %d\\n", result);
    }

    return data[0]                        // missing semicolon -> add ;
}

/* ============================================================
   SECTION B — Manual remediation required (cannot auto-fix)
   ============================================================ */

/* B1. Integer overflow + unchecked malloc + use-after-free + double-free */
void manage_data(int count, int item_size) {
    int* buf = (int*)malloc(count * item_size); // integer overflow + NULL not checked

    buf[0] = 1;
    free(buf);
    buf[0] = 0;                           // use-after-free
    free(buf);                            // double-free
}

/* B2. Division by zero */
int get_average(int sum) {
    return sum / 0;                       // division by zero
}

/* ============================================================
   ENTRY POINT — mixed fixable + manual errors
   ============================================================ */

int main() {
    char input[64]                        // missing semicolon -> add ;
    read_input(input);
    greet_user(input);

    int score;                            // uninitialized     -> int score = 0;
    printf("Score: %d\\n", score);

    int stats = compute_stats(10);
    int avg = get_average(stats)          // missing semicolon -> add ;
    printf("Average: %d\\n", avg);

    printf("Counter: %d\\n", globalCounter);
    manage_data(100, 4);
    return 0;
}
`

export default function App() {
  const [theme,        setTheme]        = useState('light')
  const [mode,         setMode]         = useState('pipeline')
  const [language,     setLanguage]     = useState('cpp')
  const [useLlm,       setUseLlm]       = useState(true)
  const [backend,      setBackend]      = useState('ollama')
  const [code,         setCode]         = useState(DEFAULT_CODE)
  const [messages,     setMessages]     = useState([])
  const [results,      setResults]      = useState({
    analysis: null, optimization: null, verification: null, security: null, pipeline: null,
  })
  const [isRunning,        setIsRunning]        = useState(false)
  const [ollamaStatus,     setOllamaStatus]     = useState(null)
  const [geminiStatus,     setGeminiStatus]     = useState(null)

  // ── Security scan state ──────────────────────────────────────────────────
  const [securityFindings, setSecurityFindings] = useState([])
  const [isScanning,       setIsScanning]       = useState(false)
  const [showFixModal,     setShowFixModal]      = useState(false)
  const [fixPreviewData,   setFixPreviewData]    = useState(null)
  const [securityTooltip,  setSecurityTooltip]  = useState(null) // {finding, x, y}
  const [syntaxErrors,     setSyntaxErrors]     = useState([])
  const [fixedErrors,      setFixedErrors]      = useState(new Set())
  const [scanHasRun,       setScanHasRun]       = useState(false)
  const [footprintEstimate, setFootprintEstimate] = useState(null)
  const [showSustainability, setShowSustainability] = useState(false)

  const abortRef          = useRef(null)
  const editorInstanceRef = useRef(null)
  const monacoInstanceRef = useRef(null)
  const lastRunModeRef    = useRef('pipeline')

  /* Debounced syntax + logic check runs on every code change */
  useEffect(() => {
    const t = setTimeout(() => setSyntaxErrors(runSyntaxCheck(code)), 600)
    return () => clearTimeout(t)
  }, [code])

  /* Merge all error sources for unified editor decorations */
  const analysisErrors = useMemo(() => {
    const findings = results.analysis?.all_findings ?? []
    return findings
      .filter(f => f.line_number || f.line)
      .map(f => ({ ...f, line: f.line_number ?? f.line, category: 'analysis' }))
  }, [results.analysis])

  const allErrors = useMemo(() => {
    const errKey = f => `${f.type}:${f.line}`
    return [
      // Normalize line_number → line so errKey always resolves correctly,
      // then filter out any security finding already fixed
      ...securityFindings
        .map(f => ({ ...f, line: f.line ?? f.line_number, category: f.category ?? 'security' }))
        .filter(f => !fixedErrors.has(errKey(f))),
      ...syntaxErrors.filter(f => !fixedErrors.has(errKey(f))),
      ...analysisErrors.filter(f => !fixedErrors.has(errKey(f))),
    ]
  }, [securityFindings, syntaxErrors, analysisErrors, fixedErrors])

  /* Fix a single error — applies the edit live inside Monaco with executeEdits */
  const handleFixError = useCallback((error) => {
    const lines   = code.split('\n')
    const lineIdx = (error.line ?? 1) - 1
    if (lineIdx < 0 || lineIdx >= lines.length) return

    const fixed = applyRuleFix(error.type, lines[lineIdx])
    if (!fixed) return

    const editor = editorInstanceRef.current
    const monaco = monacoInstanceRef.current

    if (editor && monaco) {
      const model      = editor.getModel()
      if (!model) {
        lines[lineIdx] = fixed
        setCode(lines.join('\n'))
        setFixedErrors(prev => new Set([...prev, `${error.type}:${error.line}`]))
        return
      }
      const lineNumber = lineIdx + 1
      // Replace exactly the line content (not the EOL) so the edit is surgical
      const range = new monaco.Range(
        lineNumber, 1,
        lineNumber, model.getLineMaxColumn(lineNumber)
      )
      // executeEdits gives live in-editor visual update + undo/redo support
      editor.executeEdits('rule-fix', [{ range, text: fixed, forceMoveMarkers: true }])
      editor.focus()
      // setCode will be called automatically via Monaco's onChange; no manual call needed
    } else {
      // Fallback if editor ref not yet available
      lines[lineIdx] = fixed
      setCode(lines.join('\n'))
    }

    setFixedErrors(prev => new Set([...prev, `${error.type}:${error.line}`]))
  }, [code])

  /* Fix all fixable unfixed errors at once — batched live edit in Monaco */
  const handleFixAllLocal = useCallback(() => {
    const fixable = allErrors.filter(
      e => e.fixable !== false && !fixedErrors.has(`${e.type}:${e.line}`)
    )
    if (!fixable.length) return

    // Group by line so multiple errors on the same line apply sequentially
    const byLine = {}
    for (const e of fixable) {
      const li = (e.line ?? 1) - 1
      if (!byLine[li]) byLine[li] = []
      byLine[li].push(e)
    }

    const lines    = code.split('\n')
    const newFixed = new Set(fixedErrors)
    for (const [liStr, errors] of Object.entries(byLine)) {
      const li = Number(liStr)
      let ln = lines[li]
      for (const e of errors) {
        const result = applyRuleFix(e.type, ln)
        if (result) {
          ln = result
          newFixed.add(`${e.type}:${e.line}`)
        }
      }
      lines[li] = ln
    }

    const newCode  = lines.join('\n')
    const editor   = editorInstanceRef.current
    const monaco   = monacoInstanceRef.current

    if (editor && monaco) {
      const model = editor.getModel()
      const fullRange = model.getFullModelRange()
      // Single edit operation — one undo step for the entire Fix All
      editor.executeEdits('fix-all', [{ range: fullRange, text: newCode, forceMoveMarkers: true }])
      editor.focus()
    } else {
      setCode(newCode)
    }

    setFixedErrors(newFixed)
  }, [code, allErrors, fixedErrors])

  /* Apply theme CSS attribute to <html> */
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  /* Health-check both backends on mount */
  useEffect(() => {
    setOllamaStatus({ checking: true })
    setGeminiStatus({ checking: true })
    fetch('/api/health')
      .then(r => r.json())
      .then(d => {
        setOllamaStatus(d.ollama)
        setGeminiStatus(d.gemini)
      })
      .catch(() => {
        setOllamaStatus({ available: false })
        setGeminiStatus({ available: false })
      })
  }, [])

  /* SSE event dispatcher */
  const handleEvent = useCallback((event) => {
    const { type, data, ts } = event

    /* Forward display-worthy events to the terminal */
    if (['status', 'log', 'agent_message', 'error', 'complete'].includes(type)) {
      setMessages(prev => [...prev, { type, data, ts }])
    }

    /* Populate structured result panels */
    if (type === 'analysis_result')     setResults(r => ({ ...r, analysis:     data }))
    if (type === 'optimization_result') {
      setResults(r => ({ ...r, optimization: data }))
      if (lastRunModeRef.current === 'optimize' && data?.sustainability) {
        setFootprintEstimate(data.sustainability)
      }
    }
    if (type === 'verification_result') {
      setResults(r => ({ ...r, verification: data }))
      if (lastRunModeRef.current === 'verify' && data?.sustainability) {
        setFootprintEstimate(data.sustainability)
      }
    }
    if (type === 'security_result')     setResults(r => ({ ...r, security:     data }))
    if (type === 'pipeline_result') {
      setResults(r => ({ ...r, pipeline: data }))
      if (lastRunModeRef.current === 'pipeline' && data?.sustainability) {
        setFootprintEstimate(data.sustainability)
      }
    }
    if (type === 'security_findings')   setSecurityFindings(data.findings ?? [])

    if (type === 'complete' || type === 'done') setIsRunning(false)
  }, [])

  /* Run / stop handler */
  const handleRun = useCallback(async () => {
    if (isRunning) {
      abortRef.current?.abort()
      setIsRunning(false)
      return
    }

    setIsRunning(true)
    lastRunModeRef.current = mode
    setScanHasRun(true)
    setMessages([])
    setResults({ analysis: null, optimization: null, verification: null, security: null, pipeline: null })
    setSecurityFindings([])
    setFixedErrors(new Set())
    setFootprintEstimate(null)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch('/api/stream', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ code, mode, use_llm: useLlm, language, backend }),
        signal:  controller.signal,
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({ error: 'Request failed' }))
        handleEvent({ type: 'error', data: { message: err.error || err.message || 'Request failed' }, ts: new Date().toISOString() })
        setIsRunning(false)
        return
      }

      const reader  = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer    = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()  // keep incomplete last line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            handleEvent(event)
          } catch (_) { /* ignore malformed frames */ }
        }
      }

    } catch (err) {
      if (err.name !== 'AbortError') {
        handleEvent({
          type: 'error',
          data: { message: err.message },
          ts:   new Date().toISOString(),
        })
      }
    } finally {
      setIsRunning(false)
    }
  }, [code, mode, useLlm, backend, language, isRunning, handleEvent])

  const toggleTheme = () => setTheme(t => t === 'light' ? 'dark' : 'light')

  // ── Security scan handlers ───────────────────────────────────────────────

  const handleSecurityScan = useCallback(async () => {
    setFixedErrors(new Set())
    setScanHasRun(true)
    setIsScanning(true)
    setSecurityTooltip(null)
    setMessages(prev => [...prev, {
      type: 'status',
      data: { phase: 'security', message: 'Running security scan…' },
      ts:   new Date().toISOString(),
    }])
    try {
      const resp = await fetch('/api/security-scan', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ code, language }),
      })
      if (resp.ok) {
        const data = await resp.json()
        const findings = data.findings ?? []
        setSecurityFindings(findings)
        setMessages(prev => [...prev, {
          type: 'status',
          data: { phase: 'security', message: `Security scan complete — ${findings.length} finding(s).` },
          ts:   new Date().toISOString(),
        }])
      } else {
        const err = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }))
        setMessages(prev => [...prev, {
          type: 'error',
          data: { phase: 'security', message: `Security scan failed: ${err.error ?? resp.statusText}` },
          ts:   new Date().toISOString(),
        }])
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        type: 'error',
        data: { phase: 'security', message: `Security scan error: ${err.message}` },
        ts:   new Date().toISOString(),
      }])
    } finally {
      setIsScanning(false)
    }
  }, [code, language])

  const handleFixAll = useCallback(async () => {
    const fixable = securityFindings.filter(f => f.fixable)
    if (!fixable.length) return
    setSecurityTooltip(null)
    try {
      const resp = await fetch('/api/security-fix', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ code, findings: fixable }),
      })
      if (resp.ok) {
        const data = await resp.json()
        setFixPreviewData(data)
        setShowFixModal(true)
      }
    } catch (_) { /* silent */ }
  }, [code, securityFindings])

  const handleApplyFix = useCallback((fixedCode) => {
    setCode(fixedCode)
    setShowFixModal(false)
    setFixPreviewData(null)
    // Re-scan after applying fixes
    setTimeout(() => {
      setIsScanning(true)
      fetch('/api/security-scan', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ code: fixedCode, language }),
      })
        .then(r => r.json())
        .then(d => setSecurityFindings(d.findings ?? []))
        .catch(() => {})
        .finally(() => setIsScanning(false))
    }, 100)
  }, [language])

  const handleIgnore = useCallback((finding) => {
    // Insert suppression comment on the line above the finding
    const lines  = code.split('\n')
    const lineIdx = (finding.line ?? 1) - 1
    if (lineIdx < 0 || lineIdx >= lines.length) return
    const indent = lines[lineIdx].match(/^(\s*)/)[1]
    const comment = `${indent}// SECURITY-IGNORE: ${finding.type}`
    const newLines = [...lines.slice(0, lineIdx), comment, ...lines.slice(lineIdx)]
    const newCode = newLines.join('\n')
    setCode(newCode)
    setSecurityTooltip(null)
    // Re-scan with the updated code
    setTimeout(() => {
      setIsScanning(true)
      fetch('/api/security-scan', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ code: newCode, language }),
      })
        .then(r => r.json())
        .then(d => setSecurityFindings(d.findings ?? []))
        .catch(() => {})
        .finally(() => setIsScanning(false))
    }, 100)
  }, [code, language])

  const handleGutterClick = useCallback((finding, coords) => {
    setSecurityTooltip(prev =>
      prev && prev.finding.type === finding.type && prev.finding.line === finding.line
        ? null   // toggle off if same
        : { finding, x: coords.x, y: coords.y }
    )
  }, [])

  /* Called by ResultsPanel when user accepts the optimized code */
  const handleAcceptCode = useCallback((optimizedCode) => {
    setCode(optimizedCode)
    /* Add a terminal confirmation message */
    setMessages(prev => [...prev, {
      type: 'status',
      data: { phase: 'accepted', message: 'Optimized code applied to editor.' },
      ts:   new Date().toISOString(),
    }])
  }, [])

  return (
    <div className="app">
      <Header
        mode={mode}        setMode={setMode}
        useLlm={useLlm}   setUseLlm={setUseLlm}
        backend={backend}  setBackend={setBackend}
        theme={theme}      toggleTheme={toggleTheme}
        ollamaStatus={ollamaStatus}
        geminiStatus={geminiStatus}
        isRunning={isRunning}
        onRun={handleRun}
        securityCount={securityFindings.length}
        onShowSustainability={() => setShowSustainability(true)}
        footprintEstimate={
          (
            lastRunModeRef.current === 'pipeline'
            || lastRunModeRef.current === 'optimize'
            || lastRunModeRef.current === 'verify'
          )
            ? footprintEstimate
            : null
        }
      />

      <div className="main-layout">
        <div className="editor-pane" style={{ position: 'relative' }}>
          <CodeEditor
            code={code}          setCode={setCode}
            language={language}  setLanguage={setLanguage}
            theme={theme}
            allErrors={scanHasRun ? allErrors : []}
            fixedErrors={fixedErrors}
            onGutterClick={handleGutterClick}
            onEditorMount={(editor, monaco) => {
              editorInstanceRef.current = editor
              monacoInstanceRef.current = monaco
            }}
          />
        </div>

        <div className="output-pane">
          <OutputTerminal messages={messages} isRunning={isRunning} />
        </div>
      </div>

      <div className="results-section">
        <ResultsPanel
          results={results}
          onAcceptCode={handleAcceptCode}
          messages={messages}
          securityFindings={securityFindings}
          allErrors={allErrors}
          fixedErrors={fixedErrors}
          onFixAll={handleFixAll}
          onFixAllLocal={handleFixAllLocal}
          onFixError={handleFixError}
        />
      </div>

      {securityTooltip && (
        <SecurityTooltip
          finding={securityTooltip.finding}
          x={securityTooltip.x}
          y={securityTooltip.y}
          fixableCount={securityFindings.filter(f => f.fixable).length}
          onFixAll={handleFixAll}
          onFixError={handleFixError}
          onIgnore={handleIgnore}
          onClose={() => setSecurityTooltip(null)}
        />
      )}

      {showFixModal && fixPreviewData && (
        <SecurityFixPreviewModal
          data={fixPreviewData}
          onApply={handleApplyFix}
          onCancel={() => { setShowFixModal(false); setFixPreviewData(null) }}
        />
      )}

      {showSustainability && (
        <SustainabilityDashboard onClose={() => setShowSustainability(false)} />
      )}
    </div>
  )
}

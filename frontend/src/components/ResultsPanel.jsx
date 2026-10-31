import { useState, useCallback, useRef } from 'react'
import {
  AlertTriangle, CheckCircle2, XCircle,
  FileText, Diff, ShieldCheck, MessageSquare, ShieldAlert,
  ChevronUp, ChevronDown, CheckCheck, Check, X,
  CopyCheck, Wrench,
} from 'lucide-react'
import SustainabilityBox from './SustainabilityBox'

/* ── Severity helpers ─────────────────────────────────────────────────────── */

function SeverityBadge({ severity }) {
  const s = (severity ?? 'info').toLowerCase()
  const cls = {
    high:   'severity-badge severity-high',
    medium: 'severity-badge severity-medium',
    low:    'severity-badge severity-low',
  }[s] ?? 'severity-badge severity-info'
  return <span className={cls}>{s}</span>
}

/* ── Analysis Tab ─────────────────────────────────────────────────────────── */

function AnalysisTab({ data, onFixError, fixedErrors = new Set() }) {
  if (!data) return <EmptyState icon={<FileText />} text="Run analysis to see findings." />

  const findings   = data.all_findings ?? []
  const llmCount   = findings.filter(f => f.source === 'llm').length
  const ruleCount  = findings.filter(f => f.source === 'rule').length
  const counts     = { high: 0, medium: 0, low: 0, info: 0 }
  findings.forEach(f => {
    const s = (f.severity ?? 'info').toLowerCase()
    counts[s] = (counts[s] ?? 0) + 1
  })

  return (
    <div>
      {/* Summary bar */}
      <div className="summary-bar">
        <div className="summary-item">
          <span className="summary-label">Findings:</span>
          <span className="summary-value">{findings.length}</span>
        </div>
        {counts.high > 0 && (
          <div className="summary-item">
            <span className="severity-badge severity-high">{counts.high} High</span>
          </div>
        )}
        {counts.medium > 0 && (
          <div className="summary-item">
            <span className="severity-badge severity-medium">{counts.medium} Medium</span>
          </div>
        )}
        {counts.low > 0 && (
          <div className="summary-item">
            <span className="severity-badge severity-low">{counts.low} Low</span>
          </div>
        )}
        {llmCount > 0 && (
          <div className="summary-item">
            <span style={{
              fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
              background: 'rgba(37,99,235,0.10)', color: 'var(--primary)',
              border: '1px solid rgba(37,99,235,0.22)',
            }}>{llmCount} LLM</span>
          </div>
        )}
        {ruleCount > 0 && (
          <div className="summary-item">
            <span style={{
              fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
              background: 'rgba(120,120,120,0.08)', color: 'var(--text-muted)',
              border: '1px solid rgba(120,120,120,0.18)',
            }}>{ruleCount} Rule</span>
          </div>
        )}
        {data.confidence != null && (
          <div className="summary-item">
            <span className="summary-label">Confidence:</span>
            <span className="summary-value">{Math.round((data.confidence ?? 0) * 100)}%</span>
          </div>
        )}
        {onFixError && findings.some(f => (f.line_number || f.line) && f.fixable !== false) && (
          <div className="summary-item" style={{ marginLeft: 'auto' }}>
            <button
              onClick={() => findings
                .filter(f => (f.line_number || f.line) && f.fixable !== false)
                .forEach(f => onFixError({ ...f, line: f.line_number ?? f.line }))}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '5px 12px', borderRadius: 'var(--radius-sm)',
                border: 'none', background: 'var(--primary)', color: 'white',
                fontSize: 12, fontWeight: 700, cursor: 'pointer',
                fontFamily: 'inherit', boxShadow: '0 2px 8px rgba(37,99,235,0.30)',
              }}
            >
              <Wrench size={12} strokeWidth={2.5} />
              Fix All
            </button>
          </div>
        )}
      </div>

      {findings.length === 0 ? (
        <div className="empty-state">
          <CheckCircle2 size={28} style={{ color: 'var(--accent-green)', opacity: 1 }} />
          <p>No issues found — code looks clean!</p>
        </div>
      ) : (
        <div className="findings-grid">
          {findings.map((f, i) => {
            const errLine   = f.line_number ?? f.line
            const errKey    = `${f.type ?? f.issue_type}:${errLine}`
            const isFixed   = fixedErrors.has(errKey)
            const canFix    = f.fixable !== false && !!errLine && !!onFixError
            return (
              <div key={i} className="finding-card" style={isFixed ? { borderColor: 'rgba(22,163,74,0.35)', background: 'rgba(22,163,74,0.04)' } : {}}>
                <SeverityBadge severity={f.severity} />
                <div className="finding-details">
                  <div className="finding-type" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    {(f.type ?? f.issue_type ?? 'Unknown').replace(/_/g, ' ')}
                    {f.source === 'llm' && (
                      <span style={{
                        fontSize: 9, fontWeight: 700, letterSpacing: '0.4px',
                        padding: '1px 5px', borderRadius: 3,
                        background: 'rgba(37,99,235,0.12)', color: 'var(--primary)',
                        border: '1px solid rgba(37,99,235,0.25)', textTransform: 'uppercase',
                      }}>LLM</span>
                    )}
                    {f.source === 'rule' && (
                      <span style={{
                        fontSize: 9, fontWeight: 700, letterSpacing: '0.4px',
                        padding: '1px 5px', borderRadius: 3,
                        background: 'rgba(120,120,120,0.10)', color: 'var(--text-muted)',
                        border: '1px solid rgba(120,120,120,0.2)', textTransform: 'uppercase',
                      }}>Rule</span>
                    )}
                  </div>
                  {f.description && (
                    <div className="finding-desc">{f.description}</div>
                  )}
                  {f.suggestion && (
                    <div className="finding-desc" style={{ marginTop: 3, color: 'var(--primary)' }}>
                      Suggestion: {f.suggestion}
                    </div>
                  )}
                  {errLine && (
                    <div className="finding-line">
                      Line {errLine}
                      {f.column && `:${f.column}`}
                    </div>
                  )}
                </div>
                {canFix && (
                  <button
                    onClick={() => onFixError({ ...f, line: errLine, type: f.type ?? f.issue_type })}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0,
                      padding: '4px 10px', borderRadius: 'var(--radius-sm)',
                      border: `1px solid ${isFixed ? 'rgba(22,163,74,0.4)' : 'var(--border)'}`,
                      background: isFixed ? 'rgba(22,163,74,0.10)' : 'var(--bg-surface)',
                      color: isFixed ? 'var(--accent-green)' : 'var(--primary)',
                      fontSize: 11, fontWeight: 600, cursor: 'pointer',
                      fontFamily: 'inherit', whiteSpace: 'nowrap', transition: 'all 0.15s',
                    }}
                  >
                    {isFixed
                      ? <><Check size={11} strokeWidth={3} /> Fixed</>
                      : <><Wrench size={11} strokeWidth={2} /> Fix</>
                    }
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}

      {data.conclusion && (
        <div style={{
          marginTop: 12,
          padding: '8px 12px',
          background: 'var(--bg-surface-3)',
          borderRadius: 'var(--radius-md)',
          fontSize: 12,
          color: 'var(--text-secondary)',
          borderLeft: '3px solid var(--primary)',
        }}>
          <strong style={{ color: 'var(--primary)' }}>Conclusion:</strong> {data.conclusion}
        </div>
      )}
    </div>
  )
}

/* ── Diff View ────────────────────────────────────────────────────────────── */

function DiffLine({ line }) {
  let cls = 'diff-line context'
  let marker = ' '
  if (line.startsWith('+++') || line.startsWith('---')) {
    cls = 'diff-line header'; marker = ''
  } else if (line.startsWith('@@')) {
    cls = 'diff-line header'; marker = ''
  } else if (line.startsWith('+')) {
    cls = 'diff-line added'; marker = '+'
  } else if (line.startsWith('-')) {
    cls = 'diff-line removed'; marker = '–'
  }

  const content = (line.startsWith('+') || line.startsWith('-')) ? line.slice(1) : line

  return (
    <div className={cls}>
      <span className="diff-marker">{marker}</span>
      <span>{content}</span>
    </div>
  )
}

function OptimizationTab({ data, onAcceptCode }) {
  const [accepted, setAccepted]         = useState({})   // { index: true/false }
  const [allApplied, setAllApplied]     = useState(false)

  if (!data) return <EmptyState icon={<Diff />} text="Run optimize to see the diff." />

  const transforms   = data.transformations ?? []
  const diff         = data.unified_diff ?? ''
  const diffLines    = diff.split('\n').filter(Boolean)
  const outputFile   = data.output_file ?? ''
  const optimizedCode = data.optimized_code ?? ''

  const acceptedCount  = Object.values(accepted).filter(Boolean).length
  const allIndividualAccepted = transforms.length > 0 && acceptedCount === transforms.length

  function toggleAccept(i) {
    setAccepted(prev => {
      const next = { ...prev, [i]: !prev[i] }
      const nowAll = transforms.length > 0 && Object.values(next).filter(Boolean).length === transforms.length
      if (nowAll && optimizedCode && !allApplied) {
        onAcceptCode?.(optimizedCode)
        setAllApplied(true)
      }
      return next
    })
  }

  function handleAcceptAll() {
    if (!optimizedCode) return
    const all = {}
    transforms.forEach((_, i) => { all[i] = true })
    setAccepted(all)
    setAllApplied(true)
    onAcceptCode?.(optimizedCode)
  }

  function handleRejectAll() {
    setAccepted({})
    setAllApplied(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {data.sustainability && <SustainabilityBox estimate={data.sustainability} />}
      
      {/* Summary + Accept-All / Reject-All bar */}
      <div className="summary-bar">
        <div className="summary-item">
          <span className="summary-label">Transformations:</span>
          <span className="summary-value">{transforms.length}</span>
        </div>
        {transforms.length > 0 && (
          <div className="summary-item">
            <span className="summary-label">Accepted:</span>
            <span className="summary-value" style={{ color: acceptedCount > 0 ? 'var(--accent-green)' : 'var(--text-muted)' }}>
              {acceptedCount}/{transforms.length}
            </span>
          </div>
        )}
        {outputFile && (
          <div className="summary-item">
            <span className="summary-label">Saved:</span>
            <span style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color: 'var(--primary)', fontWeight: 600 }}>
              {outputFile.split(/[\\/]/).pop()}
            </span>
          </div>
        )}

        {/* Accept All / Reject All buttons — right side */}
        {transforms.length > 0 && optimizedCode && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
            <button
              onClick={handleRejectAll}
              disabled={acceptedCount === 0}
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '5px 12px', borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
                background: acceptedCount > 0 ? 'rgba(220,38,38,0.08)' : 'var(--bg-surface-3)',
                color: acceptedCount > 0 ? 'var(--accent-red)' : 'var(--text-muted)',
                fontSize: 12, fontWeight: 600, cursor: acceptedCount > 0 ? 'pointer' : 'not-allowed',
                fontFamily: 'inherit', transition: 'all 0.15s',
              }}
              title="Clear all accepted changes"
            >
              <X size={12} strokeWidth={2.5} />
              Reject All
            </button>
            <button
              onClick={handleAcceptAll}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '5px 14px', borderRadius: 'var(--radius-sm)',
                border: 'none',
                background: allApplied ? 'var(--accent-green)' : 'var(--primary)',
                color: 'white',
                fontSize: 12, fontWeight: 700, cursor: 'pointer',
                fontFamily: 'inherit', transition: 'all 0.15s',
                boxShadow: allApplied
                  ? '0 2px 8px rgba(22,163,74,0.35)'
                  : '0 2px 8px rgba(37,99,235,0.30)',
              }}
              title="Accept all changes and apply optimized code to editor"
            >
              <CheckCheck size={13} strokeWidth={2.5} />
              {allApplied ? 'Applied to Editor' : 'Accept All Changes'}
            </button>
          </div>
        )}
      </div>

      {/* Individual transformation cards with Accept / Decline buttons */}
      {transforms.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          {transforms.map((t, i) => {
            const isAccepted = !!accepted[i]
            return (
              <div key={i} style={{
                display: 'flex',
                gap: 10,
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                background: isAccepted ? 'rgba(22,163,74,0.06)' : 'var(--bg-surface-2)',
                border: `1px solid ${isAccepted ? 'rgba(22,163,74,0.35)' : 'var(--border)'}`,
                marginBottom: 6,
                fontSize: 12,
                alignItems: 'center',
                transition: 'all 0.2s',
              }}>
                {/* Index badge */}
                <span style={{
                  width: 22, height: 22, borderRadius: '50%',
                  background: isAccepted ? 'rgba(22,163,74,0.15)' : 'var(--primary-light)',
                  color: isAccepted ? 'var(--accent-green)' : 'var(--primary)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 700, fontSize: 10, flexShrink: 0,
                }}>
                  {isAccepted ? <Check size={11} strokeWidth={3} /> : i + 1}
                </span>

                {/* Type chip */}
                <span style={{
                  color: isAccepted ? 'var(--accent-green)' : 'var(--accent-amber)',
                  fontWeight: 600, textTransform: 'uppercase', fontSize: 10,
                  minWidth: 150, letterSpacing: '0.3px',
                }}>
                  {(t.type ?? '').replace(/_/g, ' ')}
                </span>

                {/* Description */}
                <span style={{
                  color: isAccepted ? 'var(--accent-green)' : 'var(--text-secondary)',
                  flex: 1,
                }}>
                  {t.description ?? ''}
                </span>

                {/* Accept / Undo button */}
                <button
                  onClick={() => toggleAccept(i)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 5,
                    padding: '4px 10px', borderRadius: 'var(--radius-sm)',
                    border: `1px solid ${isAccepted ? 'rgba(22,163,74,0.4)' : 'var(--border)'}`,
                    background: isAccepted ? 'rgba(22,163,74,0.10)' : 'var(--bg-surface)',
                    color: isAccepted ? 'var(--accent-green)' : 'var(--text-secondary)',
                    fontSize: 11, fontWeight: 600, cursor: 'pointer',
                    fontFamily: 'inherit', whiteSpace: 'nowrap',
                    transition: 'all 0.15s',
                    flexShrink: 0,
                  }}
                >
                  {isAccepted
                    ? <><X size={11} strokeWidth={2.5} /> Undo</>
                    : <><Check size={11} strokeWidth={2.5} /> Accept</>
                  }
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* Inline notice when all individually accepted */}
      {allIndividualAccepted && allApplied && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 14px', borderRadius: 'var(--radius-md)',
          background: 'rgba(22,163,74,0.08)', border: '1px solid rgba(22,163,74,0.3)',
          marginBottom: 12, fontSize: 12, color: 'var(--accent-green)', fontWeight: 500,
        }}>
          <CopyCheck size={14} strokeWidth={2} />
          All changes accepted — optimized code applied to the editor.
        </div>
      )}

      {/* Unified Diff view */}
      {diffLines.length > 0 ? (
        <>
          <div style={{
            fontSize: 11, color: 'var(--text-muted)', marginBottom: 6,
            fontFamily: 'JetBrains Mono', letterSpacing: '0.3px',
          }}>
            Unified diff
          </div>
          <div className="diff-container">
            {diffLines.map((line, i) => <DiffLine key={i} line={line} />)}
          </div>
        </>
      ) : (
        <div className="empty-state" style={{ padding: '16px' }}>
          <p>No diff available — code may be unchanged.</p>
        </div>
      )}
    </div>
  )
}

/* ── Verification Tab ─────────────────────────────────────────────────────── */

function VerStatusBadge({ value }) {
  if (value == null) return <span className="ver-status-badge ver-skip">Skip</span>
  const ok = (typeof value === 'boolean' ? value : String(value).toLowerCase() === 'pass' || String(value).toLowerCase() === 'proven_equivalent')
  return ok
    ? <span className="ver-status-badge ver-pass">Pass</span>
    : <span className="ver-status-badge ver-fail">Fail</span>
}

function VerificationTab({ data }) {
  if (!data) return <EmptyState icon={<ShieldCheck />} text="Run verify to see results." />

  const overallStatus = (data.status ?? 'UNKNOWN').toLowerCase()
  const statusCls     = {
    pass:     'status-pill status-success',
    fail:     'status-pill status-failed',
    rollback: 'status-pill status-rollback',
  }[overallStatus] ?? 'status-pill status-partial'

  const layers = [
    {
      title:  'Layer 1 — Differential Testing',
      pass:   data.diff_passed,
      detail: data.diff_error ?? (data.diff_passed ? 'Both versions produce identical output.' : 'Output mismatch detected.'),
    },
    {
      title:  'Layer 2 — Z3 SMT Equivalence',
      pass:   data.z3_status === 'PROVEN_EQUIVALENT' ? true : data.z3_status === 'SKIPPED' ? null : false,
      detail: data.z3_status === 'SKIPPED'
        ? 'Z3 solver not available (optional).'
        : data.z3_status ?? 'Not run.',
    },
    {
      title:  'Layer 3 — Performance Benchmark',
      pass:   (() => {
        const s = data.perf_summary ?? ''
        if (!s || s.toLowerCase().includes('skipped')) return null
        return true
      })(),
      detail: data.perf_summary ?? 'Not benchmarked.',
    },
    {
      title:  'Layer 4 — LLM Semantic Verdict',
      pass:   (() => {
        const v = (data.llm_verdict ?? '').toUpperCase()
        if (!v || v === 'UNCERTAIN' || v === 'UNKNOWN') return null
        return v === 'EQUIVALENT'
      })(),
      detail: data.llm_verdict
        ? `Verdict: ${data.llm_verdict}`
        : 'LLM not queried.',
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {data.sustainability && <SustainabilityBox estimate={data.sustainability} />}

      <div className="summary-bar">
        <div className="summary-item">
          <span className="summary-label">Overall:</span>
          <span className={statusCls}>{(data.status ?? 'UNKNOWN').toUpperCase()}</span>
        </div>
        {data.conclusion && (
          <div className="summary-item" style={{ marginLeft: 'auto' }}>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{data.conclusion}</span>
          </div>
        )}
      </div>

      <div className="ver-layers">
        {layers.map((l, i) => (
          <div key={i} className="ver-layer-card">
            <div className="ver-layer-header">
              <span className="ver-layer-title">{l.title}</span>
              <VerStatusBadge value={l.pass} />
            </div>
            <div className="ver-layer-detail">{l.detail}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Security Tab ─────────────────────────────────────────────────────────── */

function RiskBadge({ risk }) {
  const r = (risk ?? 'none').toLowerCase()
  const styles = {
    critical: { background: 'rgba(220,38,38,0.12)',  color: '#dc2626', border: '1px solid rgba(220,38,38,0.35)' },
    high:     { background: 'rgba(234,88,12,0.12)',  color: '#ea580c', border: '1px solid rgba(234,88,12,0.35)' },
    medium:   { background: 'rgba(202,138,4,0.12)',  color: '#ca8a04', border: '1px solid rgba(202,138,4,0.35)' },
    low:      { background: 'rgba(22,163,74,0.10)',  color: '#16a34a', border: '1px solid rgba(22,163,74,0.30)' },
    none:     { background: 'rgba(120,120,120,0.08)', color: 'var(--text-muted)', border: '1px solid rgba(120,120,120,0.2)' },
  }
  const s = styles[r] ?? styles.none
  return (
    <span style={{ ...s, fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 3, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
      {r}
    </span>
  )
}

function computeRisk(findings) {
  if (findings.some(f => f.severity === 'high'))   return 'high'
  if (findings.some(f => f.severity === 'medium')) return 'medium'
  if (findings.length > 0)                         return 'low'
  return 'none'
}

function SecurityTab({ data, onFixAll, fixableCount = 0, onFixError, fixedErrors = new Set() }) {
  if (!data) return <EmptyState icon={<ShieldAlert />} text="Run the pipeline or click Scan Security to see findings." />

  const vulns     = data.all_vulnerabilities ?? []
  const newVulns  = new Set((data.new_vulnerabilities ?? []).map(v => `${v.type}:${v.line}`))
  const risk      = data.overall_risk ?? 'none'
  const status    = (data.status ?? 'PASS').toUpperCase()
  const statusCls = status === 'PASS' ? 'status-pill status-success' : 'status-pill status-rollback'

  const counts = { high: 0, medium: 0, low: 0 }
  vulns.forEach(v => {
    const s = (v.severity ?? 'low').toLowerCase()
    if (counts[s] != null) counts[s]++
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {data.sustainability && <SustainabilityBox estimate={data.sustainability} />}

      {/* Summary bar */}
      <div className="summary-bar">
        <div className="summary-item">
          <span className="summary-label">Status:</span>
          <span className={statusCls}>{status}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Risk:</span>
          <RiskBadge risk={risk} />
        </div>
        <div className="summary-item">
          <span className="summary-label">Findings:</span>
          <span className="summary-value">{vulns.length}</span>
        </div>
        {(data.new_vulnerabilities ?? []).length > 0 && (
          <div className="summary-item">
            <span style={{
              fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
              background: 'rgba(220,38,38,0.10)', color: 'var(--accent-red)',
              border: '1px solid rgba(220,38,38,0.25)',
            }}>
              {(data.new_vulnerabilities ?? []).length} New
            </span>
          </div>
        )}
        {counts.high > 0 && (
          <div className="summary-item">
            <span className="severity-badge severity-high">{counts.high} High</span>
          </div>
        )}
        {counts.medium > 0 && (
          <div className="summary-item">
            <span className="severity-badge severity-medium">{counts.medium} Med</span>
          </div>
        )}
        {fixableCount > 0 && onFixAll && (
          <div className="summary-item" style={{ marginLeft: 'auto' }}>
            <button
              onClick={onFixAll}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '5px 12px', borderRadius: 'var(--radius-sm)',
                border: 'none',
                background: 'var(--primary)',
                color: 'white',
                fontSize: 12, fontWeight: 700, cursor: 'pointer',
                fontFamily: 'inherit',
                boxShadow: '0 2px 8px rgba(37,99,235,0.30)',
              }}
              title={`Auto-fix ${fixableCount} fixable issue(s)`}
            >
              <Wrench size={12} strokeWidth={2.5} />
              Fix All ({fixableCount})
            </button>
          </div>
        )}
      </div>

      {vulns.length === 0 ? (
        <div className="empty-state">
          <CheckCircle2 size={28} style={{ color: 'var(--accent-green)', opacity: 1 }} />
          <p>No security vulnerabilities detected.</p>
        </div>
      ) : (
        <div className="findings-grid">
          {vulns.map((v, i) => {
            const isNew   = newVulns.has(`${v.type}:${v.line}`)
            const errLine = v.line_number ?? v.line
            const errKey  = `${v.type}:${errLine}`
            const isFixed = fixedErrors.has(errKey)
            const canFix  = v.fixable !== false && !!errLine && !!onFixError
            return (
              <div key={i} className="finding-card" style={
                isFixed ? { borderColor: 'rgba(22,163,74,0.35)', background: 'rgba(22,163,74,0.04)' }
                : isNew  ? { borderColor: 'rgba(220,38,38,0.35)', background: 'rgba(220,38,38,0.04)' }
                : {}
              }>
                <SeverityBadge severity={v.severity} />
                <div className="finding-details">
                  <div className="finding-type" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    {(v.type ?? 'unknown').replace(/_/g, ' ')}
                    {isNew && !isFixed && (
                      <span style={{
                        fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 3,
                        background: 'rgba(220,38,38,0.12)', color: 'var(--accent-red)',
                        border: '1px solid rgba(220,38,38,0.3)', textTransform: 'uppercase',
                      }}>NEW</span>
                    )}
                    {v.fixable === false && (
                      <span style={{
                        fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 3,
                        background: 'rgba(120,120,120,0.08)', color: 'var(--text-muted)',
                        border: '1px solid rgba(120,120,120,0.22)', textTransform: 'uppercase',
                        letterSpacing: '0.3px',
                      }} title="Cannot be auto-fixed — requires manual remediation">manual fix</span>
                    )}
                    {(v.cwe_id ?? v.cwe) && (
                      <span style={{
                        fontSize: 9, fontWeight: 600, padding: '1px 5px', borderRadius: 3,
                        background: 'rgba(120,120,120,0.08)', color: 'var(--text-muted)',
                        border: '1px solid rgba(120,120,120,0.2)',
                      }}>{v.cwe_id ?? v.cwe}</span>
                    )}
                    {v.source && (
                      <span style={{
                        fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 3,
                        background: 'rgba(37,99,235,0.10)', color: 'var(--primary)',
                        border: '1px solid rgba(37,99,235,0.22)', textTransform: 'uppercase',
                      }}>{v.source}</span>
                    )}
                  </div>
                  {v.description && <div className="finding-desc">{v.description}</div>}
                  {(v.recommendation ?? v.suggestion) && (
                    <div className="finding-desc" style={{ marginTop: 3, color: 'var(--primary)' }}>
                      Fix: {v.recommendation ?? v.suggestion}
                    </div>
                  )}
                  {errLine && (
                    <div className="finding-line">Line {errLine}</div>
                  )}
                </div>
                {canFix && (
                  <button
                    onClick={() => onFixError({ ...v, line: errLine })}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0,
                      padding: '4px 10px', borderRadius: 'var(--radius-sm)',
                      border: `1px solid ${isFixed ? 'rgba(22,163,74,0.4)' : 'var(--border)'}`,
                      background: isFixed ? 'rgba(22,163,74,0.10)' : 'var(--bg-surface)',
                      color: isFixed ? 'var(--accent-green)' : 'var(--primary)',
                      fontSize: 11, fontWeight: 600, cursor: 'pointer',
                      fontFamily: 'inherit', whiteSpace: 'nowrap', transition: 'all 0.15s',
                    }}
                  >
                    {isFixed
                      ? <><Check size={11} strokeWidth={3} /> Fixed</>
                      : <><Wrench size={11} strokeWidth={2} /> Fix</>
                    }
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}

      {data.llm_conclusion && (
        <div style={{
          marginTop: 12, padding: '8px 12px',
          background: 'var(--bg-surface-3)', borderRadius: 'var(--radius-md)',
          fontSize: 12, color: 'var(--text-secondary)',
          borderLeft: '3px solid var(--accent-red)',
        }}>
          <strong style={{ color: 'var(--accent-red)' }}>Security Verdict:</strong> {data.llm_conclusion}
        </div>
      )}
    </div>
  )
}

/* ── Message Log Tab ──────────────────────────────────────────────────────── */

function MessagesTab({ messages }) {
  if (!messages || messages.length === 0) {
    return <EmptyState icon={<MessageSquare />} text="No agent messages recorded yet." />
  }

  const chipClass = {
    request:      'msg-type-chip chip-request',
    response:     'msg-type-chip chip-response',
    notification: 'msg-type-chip chip-notification',
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="msg-table">
        <thead>
          <tr>
            <th>#</th>
            <th>From</th>
            <th>Type</th>
            <th>To</th>
            <th>Payload Keys</th>
          </tr>
        </thead>
        <tbody>
          {messages.map((m, i) => {
            const d = m.data ?? {}
            return (
              <tr key={i}>
                <td style={{ color: 'var(--text-muted)' }}>{d.seq ?? i + 1}</td>
                <td style={{ color: 'var(--agent-' + agentKeyFor(d.sender) + ')' }}>
                  {d.sender ?? ''}
                </td>
                <td>
                  <span className={chipClass[(d.type ?? '').toLowerCase()] ?? 'msg-type-chip'}>
                    {d.type ?? '—'}
                  </span>
                </td>
                <td style={{ color: 'var(--agent-' + agentKeyFor(d.receiver) + ')' }}>
                  {d.receiver ?? ''}
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: 10 }}>
                  {(d.payload_keys ?? []).join(', ')}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function agentKeyFor(sender = '') {
  const s = (sender ?? '').toLowerCase()
  if (s.includes('analysis'))     return 'analysis'
  if (s.includes('optim'))        return 'optimization'
  if (s.includes('verif'))        return 'verification'
  if (s.includes('pipeline'))     return 'pipeline'
  return 'log'
}

/* ── Empty state helper ───────────────────────────────────────────────────── */

function EmptyState({ icon, text }) {
  return (
    <div className="empty-state">
      {icon}
      <p>{text}</p>
    </div>
  )
}

/* ── Main ResultsPanel ────────────────────────────────────────────────────── */

const TABS = [
  { id: 'analysis',     label: 'Analysis',     icon: FileText      },
  { id: 'optimization', label: 'Optimized',    icon: Diff          },
  { id: 'verification', label: 'Verification', icon: ShieldCheck   },
  { id: 'security',     label: 'Security',     icon: ShieldAlert   },
  { id: 'messages',     label: 'Messages',     icon: MessageSquare },
]

export default function ResultsPanel({ results, onAcceptCode, messages = [], securityFindings = [], allErrors = [], fixedErrors = new Set(), onFixAll, onFixAllLocal, onFixError }) {
  const [activeTab, setActiveTab] = useState('analysis')
  const [collapsed, setCollapsed] = useState(false)

  /* Auto-switch to Optimized tab when optimization result arrives */
  const prevOptRef = useRef(null)
  if (results.optimization && prevOptRef.current !== results.optimization) {
    prevOptRef.current = results.optimization
    if (activeTab === 'analysis') setTimeout(() => setActiveTab('optimization'), 400)
  }

  /* Auto-switch to Security tab whenever new security results arrive */
  const prevSecRef = useRef(null)
  if (results.security && prevSecRef.current !== results.security) {
    prevSecRef.current = results.security
    // Always switch — each new run produces a fresh object reference
    setTimeout(() => setActiveTab('security'), 300)
  }
  /* Also switch early when scanner findings arrive (before agent finishes) */
  const prevScanRef = useRef(null)
  if (securityFindings !== prevScanRef.current) {
    prevScanRef.current = securityFindings
    if (securityFindings.length > 0) setTimeout(() => setActiveTab('security'), 150)
  }

  const agentMessages = messages.filter(m => m.type === 'agent_message')

  function countFor(tabId) {
    if (tabId === 'analysis')     return results.analysis?.all_findings?.length ?? null
    if (tabId === 'optimization') return results.optimization?.transformations?.length ?? null
    if (tabId === 'verification') return results.verification ? 1 : null
    if (tabId === 'security') {
      const n = results.security?.all_vulnerabilities?.length ?? securityFindings.length
      return n > 0 ? n : null
    }
    if (tabId === 'messages')     return agentMessages.length > 0 ? agentMessages.length : null
    return null
  }

  return (
    <>
      <div className="results-tabs-bar">
        <button
          className="icon-btn"
          onClick={() => setCollapsed(c => !c)}
          title={collapsed ? 'Expand results' : 'Collapse results'}
          style={{ marginRight: 4 }}
        >
          {collapsed
            ? <ChevronUp   size={13} strokeWidth={2} />
            : <ChevronDown size={13} strokeWidth={2} />
          }
        </button>

        {TABS.map(({ id, label, icon: Icon }) => {
          const count = countFor(id)
          return (
            <button
              key={id}
              className={`results-tab${activeTab === id ? ' active' : ''}`}
              onClick={() => { setActiveTab(id); setCollapsed(false) }}
            >
              <Icon size={12} strokeWidth={2} />
              {label}
              {count != null && <span className="tab-count">{count}</span>}
            </button>
          )
        })}

        {/* Global Fix All — only after an explicit scan or pipeline run has produced results */}
        {onFixAllLocal && (securityFindings.length > 0 || results.analysis !== null) && allErrors.some(e => e.fixable !== false && !fixedErrors.has(`${e.type}:${e.line}`)) && (
          <button
            onClick={onFixAllLocal}
            style={{
              marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6,
              padding: '4px 12px', borderRadius: 'var(--radius-sm)',
              border: 'none', background: 'var(--primary)', color: 'white',
              fontSize: 11, fontWeight: 700, cursor: 'pointer',
              fontFamily: 'inherit', boxShadow: '0 2px 6px rgba(37,99,235,0.35)',
              flexShrink: 0,
            }}
            title="Apply all rule-based fixes at once"
          >
            <Wrench size={11} strokeWidth={2.5} />
            Fix All Errors ({allErrors.filter(e => e.fixable !== false && !fixedErrors.has(`${e.type}:${e.line}`)).length})
          </button>
        )}
      </div>

      {!collapsed && (
        <div className="results-content">
          {activeTab === 'analysis'     && <AnalysisTab     data={results.analysis} onFixError={onFixError} fixedErrors={fixedErrors} />}
          {activeTab === 'optimization' && <OptimizationTab data={results.optimization} onAcceptCode={onAcceptCode} />}
          {activeTab === 'verification' && <VerificationTab data={results.verification} />}
          {activeTab === 'security'     && (() => {
            const secData = results.security ?? (securityFindings.length > 0
              ? { all_vulnerabilities: securityFindings, new_vulnerabilities: [], overall_risk: computeRisk(securityFindings), status: 'SCANNED' }
              : null)
            const fixableCount = (secData?.all_vulnerabilities ?? [])
              .filter(v => v.fixable !== false && (v.line_number ?? v.line)).length
            return <SecurityTab data={secData} onFixAll={onFixAll} fixableCount={fixableCount}
              onFixError={onFixError} fixedErrors={fixedErrors} />
          })()}
          {activeTab === 'messages'     && <MessagesTab     messages={agentMessages} />}
        </div>
      )}
    </>
  )
}

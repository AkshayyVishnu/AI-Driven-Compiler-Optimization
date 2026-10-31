import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X, ShieldCheck, CheckCircle2 } from 'lucide-react'

/* ── Diff line renderer (same pattern as ResultsPanel) ─────────────────── */
function DiffLine({ line }) {
  let cls = 'diff-line context'
  if (line.startsWith('+++') || line.startsWith('---')) cls = 'diff-line header'
  else if (line.startsWith('@@'))  cls = 'diff-line header'
  else if (line.startsWith('+'))   cls = 'diff-line added'
  else if (line.startsWith('-'))   cls = 'diff-line removed'

  const marker  = line.startsWith('+') ? '+' : line.startsWith('-') ? '–' : ' '
  const content = (line.startsWith('+') || line.startsWith('-')) ? line.slice(1) : line

  return (
    <div className={cls}>
      <span className="diff-marker">{marker}</span>
      <span>{content}</span>
    </div>
  )
}

export default function SecurityFixPreviewModal({ data, onApply, onCancel }) {
  const { fixed_code, unified_diff, fixes_applied = [] } = data
  const diffLines = (unified_diff ?? '').split('\n').filter(Boolean)
  const backdropRef = useRef(null)

  // ESC closes
  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onCancel() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onCancel])

  // Click backdrop closes
  function handleBackdropClick(e) {
    if (e.target === backdropRef.current) onCancel()
  }

  const modal = (
    <div
      ref={backdropRef}
      className="sec-modal-backdrop"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label="Security Fix Preview"
    >
      <div className="sec-modal">
        {/* Header */}
        <div className="sec-modal-header">
          <ShieldCheck size={16} strokeWidth={2} style={{ color: 'var(--accent-green)' }} />
          <span className="sec-modal-title">Security Fix Preview</span>
          <span className="sec-modal-subtitle">{fixes_applied.length} fix(es) will be applied</span>
          <button className="sec-modal-close" onClick={onCancel} aria-label="Close">
            <X size={14} strokeWidth={2.5} />
          </button>
        </div>

        {/* Fix list */}
        {fixes_applied.length > 0 && (
          <div className="sec-modal-fix-list">
            {fixes_applied.map((fix, i) => (
              <div key={i} className="sec-modal-fix-item">
                <CheckCircle2 size={12} strokeWidth={2} style={{ color: 'var(--accent-green)', flexShrink: 0 }} />
                <span className="sec-modal-fix-type">{(fix.type ?? '').replace(/_/g, ' ')}</span>
                {fix.line && <span className="sec-modal-fix-line">line {fix.line}</span>}
                <span className="sec-modal-fix-desc">{fix.description}</span>
              </div>
            ))}
          </div>
        )}

        {/* Diff */}
        <div className="sec-modal-diff-label">Unified diff</div>
        {diffLines.length > 0 ? (
          <div className="sec-modal-diff diff-container">
            {diffLines.map((line, i) => <DiffLine key={i} line={line} />)}
          </div>
        ) : (
          <div style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: 12 }}>
            No diff available.
          </div>
        )}

        {/* Actions */}
        <div className="sec-modal-actions">
          <button className="sec-modal-btn-cancel" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="sec-modal-btn-apply"
            onClick={() => onApply(fixed_code)}
            disabled={!fixed_code}
          >
            <ShieldCheck size={13} strokeWidth={2} />
            Apply to Editor
          </button>
        </div>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}

import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X, Wrench, EyeOff, ShieldAlert } from 'lucide-react'

const SEV_STYLES = {
  high:   { bg: 'rgba(220,38,38,0.12)',  color: '#dc2626', border: 'rgba(220,38,38,0.35)' },
  medium: { bg: 'rgba(234,88,12,0.12)',  color: '#ea580c', border: 'rgba(234,88,12,0.35)' },
  low:    { bg: 'rgba(202,138,4,0.12)',  color: '#ca8a04', border: 'rgba(202,138,4,0.35)' },
}

export default function SecurityTooltip({
  finding,
  x, y,
  fixableCount,
  onFixAll,
  onFixError,
  onIgnore,
  onClose,
}) {
  const ref = useRef(null)

  // Close on outside click
  useEffect(() => {
    function onMouseDown(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [onClose])

  // Close on ESC
  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const sev    = (finding.severity ?? 'low').toLowerCase()
  const style  = SEV_STYLES[sev] ?? SEV_STYLES.low

  // Clamp position so tooltip stays on screen
  const TOOLTIP_W = 320
  const TOOLTIP_H = 200
  const clampedX  = Math.min(x, window.innerWidth  - TOOLTIP_W - 12)
  const clampedY  = y + TOOLTIP_H > window.innerHeight
    ? y - TOOLTIP_H - 8
    : y + 4

  const tooltip = (
    <div
      ref={ref}
      className="sec-tooltip"
      style={{ left: clampedX, top: clampedY }}
      role="dialog"
      aria-label={`Security finding: ${finding.type}`}
    >
      {/* Header */}
      <div className="sec-tooltip-header">
        <ShieldAlert size={13} strokeWidth={2} style={{ color: style.color, flexShrink: 0 }} />
        <span
          className="sec-tooltip-sev"
          style={{ background: style.bg, color: style.color, border: `1px solid ${style.border}` }}
        >
          {sev.toUpperCase()}
        </span>
        <span className="sec-tooltip-type">
          {(finding.type ?? '').replace(/_/g, ' ')}
        </span>
        {finding.cwe_id && (
          <span className="sec-tooltip-cwe">{finding.cwe_id}</span>
        )}
        <button className="sec-tooltip-close" onClick={onClose} aria-label="Close">
          <X size={12} strokeWidth={2.5} />
        </button>
      </div>

      {/* Body */}
      <div className="sec-tooltip-body">
        {finding.line && (
          <div className="sec-tooltip-line">Line {finding.line}</div>
        )}
        <p className="sec-tooltip-desc">{finding.description}</p>
        {finding.recommendation && (
          <p className="sec-tooltip-rec">
            <strong>Fix:</strong> {finding.recommendation}
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="sec-tooltip-actions">
        {finding.fixable !== false && onFixError && (
          <button
            className="sec-tooltip-btn sec-tooltip-btn-fix"
            onClick={() => { onFixError(finding); onClose() }}
          >
            <Wrench size={12} strokeWidth={2} />
            Fix This
          </button>
        )}
        {fixableCount > 1 && (
          <button
            className="sec-tooltip-btn sec-tooltip-btn-fix"
            onClick={onFixAll}
            style={{ opacity: 0.85 }}
          >
            <Wrench size={12} strokeWidth={2} />
            Fix All ({fixableCount})
          </button>
        )}
        <button
          className="sec-tooltip-btn sec-tooltip-btn-ignore"
          onClick={() => onIgnore(finding)}
        >
          <EyeOff size={12} strokeWidth={2} />
          Ignore
        </button>
      </div>
    </div>
  )

  return createPortal(tooltip, document.body)
}

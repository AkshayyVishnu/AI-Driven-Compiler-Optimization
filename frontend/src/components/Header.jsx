import { Sun, Moon, Play, Cpu, Search, Zap, ShieldCheck, GitBranch, Brain, Code2, Sparkles, ShieldAlert, Leaf } from 'lucide-react'

const MODES = [
  { id: 'pipeline', label: 'Full Pipeline', icon: GitBranch  },
  { id: 'analyze',  label: 'Analyze',       icon: Search     },
  { id: 'optimize', label: 'Optimize',      icon: Zap        },
  { id: 'verify',   label: 'Verify',        icon: ShieldCheck },
  { id: 'security', label: 'Security',      icon: ShieldAlert },
]

export default function Header({
  mode, setMode,
  useLlm, setUseLlm,
  backend, setBackend,
  theme, toggleTheme,
  ollamaStatus,
  geminiStatus,
  isRunning,
  onRun,
  securityCount,
  footprintEstimate,
  onShowSustainability,
}) {

  /* Status indicator reflects the active backend */
  const activeStatus = backend === 'gemini' ? geminiStatus : ollamaStatus

  const dotClass = activeStatus?.checking
    ? 'checking'
    : activeStatus?.available
      ? 'online'
      : 'offline'

  const dotLabel = activeStatus?.checking
    ? 'Checking…'
    : activeStatus?.available
      ? `LLM Online (${activeStatus.model ?? 'unknown'})`
      : `LLM Offline (${backend === 'gemini' ? 'Gemini' : 'Ollama'})`

  return (
    <header className="header">
      {/* Logo */}
      <div className="header-logo">
        <div className="logo-icon">
          <Cpu size={17} strokeWidth={2.5} />
        </div>
        <div>
          <div className="logo-text">DeepCompile</div>
          <div className="logo-sub">Optimization Studio</div>
        </div>
      </div>

      <div className="header-divider" />

      {/* Mode tabs */}
      <nav className="mode-tabs" aria-label="Pipeline mode">
        {MODES.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`mode-tab${mode === id ? ' active' : ''}${id === 'security' && securityCount > 0 ? ' has-findings' : ''}`}
            onClick={() => setMode(id)}
            aria-pressed={mode === id}
          >
            <Icon size={13} strokeWidth={2} />
            {label}
            {id === 'security' && securityCount > 0 && (
              <span className="scan-count-badge">{securityCount}</span>
            )}
          </button>
        ))}
      </nav>

      <div className="header-divider" />

      {/* LLM toggle */}
      <div className="llm-toggle" role="group" aria-label="Inference mode">
        <button
          className={`llm-btn${useLlm ? ' active' : ''}`}
          onClick={() => setUseLlm(true)}
          title="Use an LLM backend for enhanced analysis"
        >
          <Brain size={12} strokeWidth={2} />
          LLM
        </button>
        <button
          className={`llm-btn${!useLlm ? ' active' : ''}`}
          onClick={() => setUseLlm(false)}
          title="Use rule-based heuristics and regex patterns only"
        >
          <Code2 size={12} strokeWidth={2} />
          Heuristics
        </button>
      </div>

      <div className="header-divider" />

      {/* Backend selector */}
      <div className="llm-toggle" role="group" aria-label="LLM backend">
        <button
          className={`llm-btn${backend === 'ollama' ? ' active' : ''}`}
          onClick={() => setBackend('ollama')}
          title="Qwen 2.5 Coder 7B via local Ollama"
          disabled={!useLlm}
        >
          <Cpu size={12} strokeWidth={2} />
          Qwen 2.5
        </button>
        <button
          className={`llm-btn${backend === 'gemini' ? ' active' : ''}`}
          onClick={() => setBackend('gemini')}
          title="Google Gemini API (requires GEMINI_API_KEY)"
          disabled={!useLlm}
        >
          <Sparkles size={12} strokeWidth={2} />
          Gemini
        </button>
      </div>

      <div className="header-spacer" />

      {/* Backend status */}
      <div className="ollama-status" title={activeStatus?.base_url ?? activeStatus?.backend ?? ''}>
        <span className={`status-dot ${dotClass}`} />
        {dotLabel}
      </div>

      {footprintEstimate && (
        <div className="header-footprint" onClick={onShowSustainability} title="Click to view detailed sustainability benchmarks">
          <span className="header-footprint-chip">
            <Leaf size={12} strokeWidth={2.2} />
            {footprintEstimate.action_label}
          </span>
          <span className="header-footprint-metric">
            Energy <strong>{footprintEstimate.energy_display}</strong>
          </span>
          <span className="header-footprint-metric">
            Emissions <strong>{footprintEstimate.emissions_display}</strong>
          </span>
        </div>
      )}

      {/* Theme toggle */}
      <button
        className="theme-toggle"
        onClick={toggleTheme}
        aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        title={theme === 'light' ? 'Dark mode (black & blue)' : 'Light mode (white & blue)'}
      >
        {theme === 'light' ? <Moon size={15} strokeWidth={2} /> : <Sun size={15} strokeWidth={2} />}
      </button>

      {/* Run / Stop button */}
      <button
        className={`run-btn${isRunning ? ' running' : ''}`}
        onClick={onRun}
        aria-label={isRunning ? 'Stop' : mode === 'security' ? 'Scan Security' : 'Run pipeline'}
      >
        {isRunning ? (
          <>
            <span className="spinner" />
            Stop
          </>
        ) : mode === 'security' ? (
          <>
            <ShieldAlert size={13} strokeWidth={2} />
            Scan
          </>
        ) : (
          <>
            <Play size={13} strokeWidth={2.5} fill="white" />
            Run
          </>
        )}
      </button>
    </header>
  )
}

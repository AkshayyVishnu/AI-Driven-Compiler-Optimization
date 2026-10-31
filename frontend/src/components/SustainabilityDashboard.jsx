import React, { useState, useEffect } from 'react'
import { Leaf, Zap, BarChart3, Cloud, Cpu, X, TrendingDown, Info } from 'lucide-react'

export default function SustainabilityDashboard({ onClose }) {
  const [benchmarks, setBenchmarks] = useState(null)
  const [loading, setLoading] = useState(true)
  const [unit, setUnit] = useState('mwh') // 'mwh' or 'mg'

  useEffect(() => {
    fetch('/api/sustainability-benchmarks')
      .then(r => r.json())
      .then(data => {
        setBenchmarks(data)
        setLoading(false)
      })
      .catch(err => console.error("Failed to load benchmarks:", err))
  }, [])

  if (loading) return null

  const scenarios = Object.entries(benchmarks)

  // Calculate chart scaling and ticks globally for consistency
  const rawMax = Math.max(...scenarios.map(([_, s]) => 
    unit === 'mwh' 
      ? (s.standard.local_mwh + s.standard.cloud_mwh) 
      : s.standard.emissions_mg
  ))

  let chartMax, ticks
  const chartWidth = 300

  if (unit === 'mg') {
    // Fixed interval of 5 for emissions
    const interval = 5
    const tickCount = Math.ceil((rawMax * 1.1) / interval)
    chartMax = tickCount * interval
    ticks = Array.from({ length: tickCount + 1 }, (_, i) => i * interval)
  } else {
    // Dynamic interval for energy
    chartMax = rawMax * 1.1
    const tickCount = 5
    ticks = Array.from({ length: tickCount + 1 }, (_, i) => (chartMax / tickCount) * i)
  }

  const scale = chartWidth / chartMax

  return (
    <div className="sustainability-dashboard-overlay">
      <div className="sustainability-dashboard">
        <header className="dashboard-header">
          <div className="dashboard-title">
            <BarChart3 className="text-green-500" size={20} />
            <h2>Green AI Benchmarks</h2>
            <span className="method-tag">CodeCarbon RAPL + Cloud Estimation</span>
          </div>
          <div className="dashboard-actions">
             <div className="unit-toggle">
                <button 
                  className={unit === 'mwh' ? 'active' : ''} 
                  onClick={() => setUnit('mwh')}
                >Energy (mWh)</button>
                <button 
                  className={unit === 'mg' ? 'active' : ''} 
                  onClick={() => setUnit('mg')}
                >Emissions (mg)</button>
             </div>
             <button className="close-btn" onClick={onClose}><X size={20} /></button>
          </div>
        </header>

        <div className="dashboard-content">
          <div className="dashboard-grid">
            {scenarios.map(([key, s]) => {
              const standardVal = unit === 'mwh' 
                ? (s.standard.local_mwh + s.standard.cloud_mwh) 
                : s.standard.emissions_mg
              const optimizedVal = unit === 'mwh' 
                ? (s.optimized.local_mwh + s.optimized.cloud_mwh) 
                : s.optimized.emissions_mg
              
              const savingsPct = Math.round(((standardVal - optimizedVal) / standardVal) * 100)
              const barHeight = 18
              const axisHeight = 20

              return (
                <div key={key} className="scenario-card">
                  <div className="scenario-info">
                    <h3>{s.name}</h3>
                    <p>{s.description}</p>
                    <div className="savings-badge">
                        <TrendingDown size={14} />
                        {savingsPct}% Reduction
                    </div>
                  </div>

                  <div className="scenario-viz">
                    <div className="viz-row">
                      <span className="viz-label">Standard</span>
                      <svg width={chartWidth} height={barHeight}>
                        <rect 
                           x={0} y={0} 
                           width={unit === 'mwh' ? s.standard.cloud_mwh * scale : standardVal * scale} 
                           height={barHeight} 
                           fill={unit === 'mwh' ? "var(--accent-purple)" : "var(--accent-cyan)"} 
                           rx={3} 
                        />
                        {unit === 'mwh' && (
                          <rect 
                             x={s.standard.cloud_mwh * scale} y={0} 
                             width={s.standard.local_mwh * scale} 
                             height={barHeight} 
                             fill="var(--primary)" 
                             rx={3} 
                          />
                        )}
                      </svg>
                      <span className="viz-value">{standardVal.toFixed(1)}</span>
                    </div>

                    <div className="viz-row">
                      <span className="viz-label">Optimized</span>
                      <svg width={chartWidth} height={barHeight}>
                        <rect 
                           x={0} y={0} 
                           width={unit === 'mwh' ? s.optimized.cloud_mwh * scale : optimizedVal * scale} 
                           height={barHeight} 
                           fill={unit === 'mwh' ? "var(--accent-purple)" : "var(--accent-cyan)"} 
                           rx={3} 
                        />
                        {unit === 'mwh' && (
                          <rect 
                             x={s.optimized.cloud_mwh * scale} y={0} 
                             width={s.optimized.local_mwh * scale} 
                             height={barHeight} 
                             fill="var(--primary)" 
                             rx={3} 
                          />
                        )}
                      </svg>
                      <span className="viz-value optimized">{optimizedVal.toFixed(1)}</span>
                    </div>

                    {/* Axis Row */}
                    <div className="viz-row axis-row">
                      <span className="viz-label"></span>
                      <svg width={chartWidth} height={axisHeight}>
                        <line x1={0} y1={0} x2={chartWidth} y2={0} stroke="var(--border)" strokeWidth={1} />
                        {ticks.map((t, i) => (
                          <g key={i}>
                            <line 
                              x1={t * scale} y1={0} 
                              x2={t * scale} y2={5} 
                              stroke="var(--border)" 
                              strokeWidth={1} 
                            />
                            <text 
                              x={t * scale} y={15} 
                              fontSize="9" 
                              fill="var(--text-muted)" 
                              textAnchor={i === 0 ? "start" : i === ticks.length - 1 ? "end" : "middle"}
                            >
                              {Math.round(t)}
                            </text>
                          </g>
                        ))}
                      </svg>
                      <span className="viz-unit">{unit}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <aside className="dashboard-sidebar">
             <div className="insight-box">
                <h4><Info size={16} /> How it works</h4>
                <p>
                  Standard heuristics often over-rely on LLM calls for simple tasks. 
                  Our **Optimized Heuristics** use local regex and AST patterns 
                  first, reducing remote token usage by up to 80% while 
                  maintaining verification integrity.
                </p>
             </div>
             <div className="legend-box">
                <h4>Legend</h4>
                <div className="legend-item">
                  <div className="color-box" style={{background: 'var(--primary)'}}></div>
                  <span>Local CPU (RAPL)</span>
                </div>
                <div className="legend-item">
                  <div className="color-box" style={{background: 'var(--accent-purple)'}}></div>
                  <span>Cloud LLM (Estimated)</span>
                </div>
                <div className="legend-item">
                  <div className="color-box" style={{background: 'var(--accent-cyan)'}}></div>
                  <span>Carbon mg CO2e</span>
                </div>
             </div>
          </aside>
        </div>
      </div>
    </div>
  )
}

import React from 'react'
import { BatteryCharging, Cloud, Leaf, Cpu, Zap } from 'lucide-react'

export default function SustainabilityBox({ estimate }) {
  if (!estimate) return null

  const {
    energy_display,
    emissions_display,
    local_energy_mwh,
    llm_energy_mwh,
    method,
    is_measured,
    assumptions
  } = estimate

  const total = (local_energy_mwh || 0) + (llm_energy_mwh || 0)
  const localPct = total > 0 ? Math.round((local_energy_mwh / total) * 100) : 0
  const llmPct = total > 0 ? Math.round((llm_energy_mwh / total) * 100) : 0

  return (
    <div className="sustainability-box" role="status" aria-live="polite">
      <div className="sustainability-header">
        <div className="sustainability-title">
          <Leaf size={16} className="text-green-500" />
          <span>Sustainability Footprint</span>
        </div>
        {is_measured && (
          <span className="live-badge">
            <Zap size={10} fill="currentColor" /> LIVE RAPL
          </span>
        )}
      </div>

      <div className="sustainability-grid">
        <div className="sustainability-item">
          <span className="sustainability-label">
            <BatteryCharging size={14} strokeWidth={2.2} />
            Total Energy
          </span>
          <strong>{energy_display}</strong>
        </div>
        <div className="sustainability-item">
          <span className="sustainability-label">
            <Cloud size={14} strokeWidth={2.2} />
            Est. Emissions
          </span>
          <strong>{emissions_display}</strong>
        </div>
      </div>

      <div className="sustainability-breakdown">
        <div className="breakdown-bar">
          <div 
            className="breakdown-segment local" 
            style={{ width: `${localPct}%` }}
            title={`Local Heuristics: ${local_energy_mwh} mWh`}
          />
          <div 
            className="breakdown-segment llm" 
            style={{ width: `${llmPct}%` }}
            title={`Cloud LLM: ${llm_energy_mwh} mWh`}
          />
        </div>
        <div className="breakdown-labels">
          <span><Cpu size={10} /> Local ({localPct}%)</span>
          <span><Cloud size={10} /> Cloud LLM ({llmPct}%)</span>
        </div>
      </div>

      <p className="sustainability-box-note">
        {method}
      </p>
      
      {assumptions && (
         <div className="sustainability-assumptions">
            Grid: {is_measured ? "Local RAPL (385g/kWh)" : "Avg (420g/kWh)"} | Cloud (440g/kWh)
         </div>
      )}
    </div>
  )
}

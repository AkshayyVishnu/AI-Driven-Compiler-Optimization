"""
Rule-based energy and emissions estimator for DeepCompile runs.

This does not attempt hardware-level metering. Instead, it produces a stable,
deterministic estimate from source complexity, stage timings, and action type
so the UI can surface a consistent "run footprint" after optimize, verify, or
full-pipeline runs.
"""

from __future__ import annotations

from typing import Any, Dict


def estimate_run_footprint(
    action: str,
    source_code: str,
    result: Dict[str, Any] | None = None,
    use_llm: bool = False,
    hardware_metrics: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    result = result or {}
    action = (action or "run").lower()

    lines = [line for line in source_code.splitlines() if line.strip()]
    line_count = max(1, len(lines))
    char_count = len(source_code)
    transform_count = len(result.get("transformations", []) or [])
    finding_count = len(result.get("all_findings", []) or [])

    stage_timings = result.get("stage_timings", {}) or {}
    total_seconds, llm_seconds = _sum_stage_timings(stage_timings)
    non_llm_seconds = max(0.0, total_seconds - llm_seconds)

    # 1. Rule-based Heuristics for Baseline
    if action == "optimize":
        baseline_wh = 0.010
        complexity_coeff = 0.00010
        action_bias_wh = 0.006
    elif action == "verify":
        baseline_wh = 0.015
        complexity_coeff = 0.00012
        action_bias_wh = 0.010
    elif action == "pipeline":
        baseline_wh = 0.020
        complexity_coeff = 0.00013
        action_bias_wh = 0.014
    else:
        baseline_wh = 0.009
        complexity_coeff = 0.00008
        action_bias_wh = 0.005

    complexity_units = (
        line_count
        + (char_count / 90.0)
        + (transform_count * 10.0)
        + (finding_count * 6.0)
    )
    complexity_wh = min(0.18, complexity_units * complexity_coeff)

    # 2. Local Hardware Monitoring (RAPL/CodeCarbon)
    # If hardware_metrics is present, we use it for local energy (non-LLM)
    local_energy_wh = 0.0
    is_measured = False
    if hardware_metrics and hardware_metrics.get("hardware_measured"):
        local_energy_wh = hardware_metrics.get("energy_kwh", 0.0) * 1000.0
        is_measured = True
    else:
        # Fallback to timing-based rule
        local_energy_wh = (non_llm_seconds * 24.0) / 3600.0 + baseline_wh + action_bias_wh + complexity_wh

    # 3. LLM Remote Footprint (Cloud/External)
    # This is always an estimate because hardware monitoring cannot see remote server usage
    llm_energy_wh = (llm_seconds * 58.0) / 3600.0
    if use_llm or llm_seconds > 0:
         llm_energy_wh += 0.010
    
    total_energy_wh = local_energy_wh + llm_energy_wh
    
    # 4. Emissions Calculation (Hybrid Carbon Intensity Model)
    # Different grids have different intensities. 
    # Local (User's Grid) vs Cloud (Data Center Grid)
    local_intensity = 385.0  # e.g., Regional mix
    cloud_intensity = 440.0  # e.g., High-performance data center mix
    
    # Add a tiny deterministic "fluctuation" based on time/char count 
    # so it's not a perfectly flat multiplier of 0.42
    variance = 1.0 + ((char_count % 10) - 5) / 500.0 
    
    local_emissions_g = (local_energy_wh * (local_intensity / 1000.0)) * variance
    cloud_emissions_g = (llm_energy_wh * (cloud_intensity / 1000.0))
    
    total_emissions_g = local_emissions_g + cloud_emissions_g

    energy_mwh = round(total_energy_wh * 1000.0, 1)
    emissions_mg = round(total_emissions_g * 1000.0, 1)

    return {
        "action": action,
        "action_label": (
            "Optimization" if action == "optimize"
            else "Verification" if action == "verify"
            else "Full Pipeline" if action == "pipeline"
            else action.title()
        ),
        "total_energy_mwh": energy_mwh,
        "local_energy_mwh": round(local_energy_wh * 1000.0, 1),
        "llm_energy_mwh": round(llm_energy_wh * 1000.0, 1),
        "total_emissions_mg": emissions_mg,
        "energy_display": f"{energy_mwh:.1f} mWh",
        "emissions_display": f"{emissions_mg:.1f} mg CO2e",
        "is_measured": is_measured,
        "method": "Hybrid: Hardware Monitoring (RAPL) + LLM Cloud Estimation" if is_measured else "Rule-based estimate from timings and code size.",
        "assumptions": {
            "local_grid_intensity": local_intensity,
            "cloud_grid_intensity": cloud_intensity,
            "source_lines": line_count,
            "timed_seconds": round(total_seconds, 4),
            "is_hardware_active": is_measured
        },
    }


def _sum_stage_timings(stage_timings: Dict[str, Any]) -> tuple[float, float]:
    total = 0.0
    llm_total = 0.0

    for key, value in stage_timings.items():
        if isinstance(value, dict):
            nested_total, nested_llm = _sum_stage_timings(value)
            total += nested_total
            llm_total += nested_llm
            continue

        if not isinstance(value, (int, float)):
            continue

        numeric = max(0.0, float(value))
        total += numeric
        if "llm" in str(key).lower():
            llm_total += numeric

    return total, llm_total

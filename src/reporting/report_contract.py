"""
Shared explainability report contract for CLI, UI, and batch exports.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


@dataclass
class ExplainabilityReport:
    file_path: str
    status: str
    workflow_status: str
    findings: List[Dict[str, Any]] = field(default_factory=list)
    transformations: List[Dict[str, Any]] = field(default_factory=list)
    verification_verdict: Dict[str, Any] = field(default_factory=dict)
    security_verdict: Dict[str, Any] = field(default_factory=dict)
    reasoning_summary: List[str] = field(default_factory=list)
    unified_diff: str = ""
    output_artifact_path: str = ""
    iteration_count: int = 0
    stop_reason: str = ""
    review_required: bool = False
    escalation_reasons: List[str] = field(default_factory=list)
    cache_hits: Dict[str, bool] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_explainability_report(
    file_path: str,
    pipeline_result: Any,
    orchestration: Optional[Dict[str, Any]] = None,
) -> ExplainabilityReport:
    orchestration = orchestration or {}
    analysis = getattr(pipeline_result, "analysis_report", {}) or {}
    optimization = getattr(pipeline_result, "optimization_report", {}) or {}
    verification = getattr(pipeline_result, "verification_report", {}) or {}
    security = getattr(pipeline_result, "security_report", {}) or {}

    reasoning_summary: List[str] = []
    if analysis.get("conclusion"):
        reasoning_summary.append("Analysis: " + analysis["conclusion"])
    if optimization.get("conclusion"):
        reasoning_summary.append("Optimization: " + optimization["conclusion"])
    if verification.get("conclusion"):
        reasoning_summary.append("Verification: " + verification["conclusion"])
    if security.get("summary"):
        reasoning_summary.append("Security: " + security["summary"].splitlines()[0])

    return ExplainabilityReport(
        file_path=file_path,
        status=getattr(pipeline_result, "status", "unknown"),
        workflow_status=orchestration.get("workflow_status", getattr(pipeline_result, "status", "unknown").upper()),
        findings=analysis.get("all_findings", []),
        transformations=optimization.get("transformations", []),
        verification_verdict=verification,
        security_verdict=security,
        reasoning_summary=reasoning_summary,
        unified_diff=optimization.get("unified_diff", ""),
        output_artifact_path=optimization.get("output_file", ""),
        iteration_count=orchestration.get("iteration_count", 0),
        stop_reason=orchestration.get("stop_reason", ""),
        review_required=bool(orchestration.get("review_required", False)),
        escalation_reasons=orchestration.get("escalation_reasons", []),
        cache_hits=orchestration.get("cache_hits", {}),
    )

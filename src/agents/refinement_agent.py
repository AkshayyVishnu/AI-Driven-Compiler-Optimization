"""
Refinement agent with bounded retry logic and convergence guardrails.
"""

from __future__ import annotations

import hashlib
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent_framework import BaseAgent, ContextManager
from src.agents.analysis_agent import AnalysisAgent
from src.agents.optimization_agent import OptimizationAgent
from src.agents.security_agent import SecurityAgent
from src.agents.verification_agent import VerificationAgent

logger = logging.getLogger(__name__)


@dataclass
class RefinementCycle:
    cycle: int
    strategy: str
    status: str
    optimization_confidence: float
    diff_signature: str
    stop_reason: str = ""


@dataclass
class RefinementResult:
    status: str
    stop_reason: str
    cycle_count: int
    cycles: List[RefinementCycle] = field(default_factory=list)
    final_analysis: Dict[str, Any] = field(default_factory=dict)
    final_optimization: Dict[str, Any] = field(default_factory=dict)
    final_verification: Dict[str, Any] = field(default_factory=dict)
    final_security: Dict[str, Any] = field(default_factory=dict)
    escalation_reasons: List[str] = field(default_factory=list)
    review_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "stop_reason": self.stop_reason,
            "cycle_count": self.cycle_count,
            "cycles": [
                {
                    "cycle": cycle.cycle,
                    "strategy": cycle.strategy,
                    "status": cycle.status,
                    "optimization_confidence": cycle.optimization_confidence,
                    "diff_signature": cycle.diff_signature,
                    "stop_reason": cycle.stop_reason,
                }
                for cycle in self.cycles
            ],
            "final_analysis": self.final_analysis,
            "final_optimization": self.final_optimization,
            "final_verification": self.final_verification,
            "final_security": self.final_security,
            "escalation_reasons": self.escalation_reasons,
            "review_required": self.review_required,
        }


class RefinementAgent(BaseAgent):
    def __init__(self, agent_id: str, context_manager: ContextManager, llm_client=None):
        self.llm = llm_client
        super().__init__(agent_id, "refinement", context_manager)

    def get_capabilities(self) -> List[str]:
        return [
            "bounded_refinement_cycles",
            "rollback_trigger_detection",
            "oscillation_detection",
            "safe_rule_only_retry",
        ]

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        original_code = input_data.get("original_code", "")
        file_path = input_data.get("file_path", "<unknown>")
        analysis_report = deepcopy(input_data.get("analysis_report") or {})
        previous_optimization = deepcopy(input_data.get("previous_optimization") or {})
        previous_verification = deepcopy(input_data.get("previous_verification") or {})
        previous_security = deepcopy(input_data.get("previous_security") or {})
        max_cycles = int(input_data.get("max_cycles", 3))
        low_conf_threshold = float(input_data.get("low_conf_threshold", 0.8))

        if not original_code:
            return RefinementResult(
                status="ABORTED",
                stop_reason="missing_original_code",
                cycle_count=0,
                escalation_reasons=["Missing original code for refinement."],
                review_required=True,
            ).to_dict()

        seen_diffs = set()
        cycles: List[RefinementCycle] = []
        last_score = _score_from_reports(previous_verification, previous_security)
        last_confidence = float(previous_optimization.get("confidence", 0.0))
        escalation_reasons: List[str] = []
        final_analysis = analysis_report
        final_optimization = previous_optimization
        final_verification = previous_verification
        final_security = previous_security

        if (
            previous_verification.get("status") == "PASS"
            and previous_security.get("status", "PASS") == "PASS"
            and last_confidence >= low_conf_threshold
        ):
            return RefinementResult(
                status="PASS",
                stop_reason="no_refinement_needed",
                cycle_count=0,
                final_analysis=analysis_report,
                final_optimization=previous_optimization,
                final_verification=previous_verification,
                final_security=previous_security,
            ).to_dict()

        for cycle_index in range(1, max_cycles + 1):
            strategy = "rule_only_retry" if cycle_index == 1 else "llm_guided_retry"
            cycle_context = ContextManager()
            cycle_analysis_agent = AnalysisAgent(f"analysis_refine_{cycle_index}", cycle_context, self.llm)
            cycle_optimization_agent = OptimizationAgent(
                f"optimization_refine_{cycle_index}",
                cycle_context,
                self.llm,
            )
            cycle_verification_agent = VerificationAgent(
                f"verification_refine_{cycle_index}",
                cycle_context,
                self.llm,
            )
            cycle_security_agent = SecurityAgent(
                f"security_refine_{cycle_index}",
                cycle_context,
                self.llm,
            )

            if strategy == "rule_only_retry":
                cycle_analysis_agent.llm._available = False
                cycle_optimization_agent.llm._available = False

            cycle_analysis = cycle_analysis_agent.process({
                "source_code": original_code,
                "file_path": file_path,
            })
            cycle_analysis = _merge_feedback_findings(
                cycle_analysis,
                previous_verification,
                previous_security,
            )
            cycle_optimization = cycle_optimization_agent.process({
                "source_code": original_code,
                "file_path": file_path,
                "analysis_report": cycle_analysis,
            })
            diff_signature = hashlib.sha256(
                cycle_optimization.get("unified_diff", "").encode("utf-8")
            ).hexdigest()

            if diff_signature in seen_diffs:
                escalation_reasons.append("Repeated diff pattern detected during refinement.")
                cycles.append(RefinementCycle(
                    cycle=cycle_index,
                    strategy=strategy,
                    status="ESCALATE",
                    optimization_confidence=float(cycle_optimization.get("confidence", 0.0)),
                    diff_signature=diff_signature,
                    stop_reason="repeated_diff_pattern",
                ))
                return RefinementResult(
                    status="ESCALATE",
                    stop_reason="repeated_diff_pattern",
                    cycle_count=len(cycles),
                    cycles=cycles,
                    final_analysis=final_analysis,
                    final_optimization=final_optimization,
                    final_verification=final_verification,
                    final_security=final_security,
                    escalation_reasons=escalation_reasons,
                    review_required=True,
                ).to_dict()

            seen_diffs.add(diff_signature)
            cycle_verification = cycle_verification_agent.process({
                "original_code": original_code,
                "optimized_code": cycle_optimization.get("optimized_code", original_code),
                "file_path": file_path,
            })
            final_candidate = (
                original_code
                if cycle_verification.get("status") in ("ROLLBACK", "FAIL")
                else cycle_optimization.get("optimized_code", original_code)
            )
            cycle_security = cycle_security_agent.process({
                "original_code": original_code,
                "optimized_code": final_candidate,
                "file_path": file_path,
            })

            candidate_score = _score_from_reports(cycle_verification, cycle_security)
            candidate_confidence = float(cycle_optimization.get("confidence", 0.0))
            cycle_status = (
                "PASS"
                if cycle_verification.get("status") == "PASS"
                and cycle_security.get("status") == "PASS"
                else "RETRY"
            )
            cycles.append(RefinementCycle(
                cycle=cycle_index,
                strategy=strategy,
                status=cycle_status,
                optimization_confidence=candidate_confidence,
                diff_signature=diff_signature,
            ))

            if cycle_security.get("status") == "ROLLBACK":
                escalation_reasons.append("Security rollback triggered during refinement.")
                return RefinementResult(
                    status="ROLLBACK",
                    stop_reason="rollback_trigger",
                    cycle_count=len(cycles),
                    cycles=cycles,
                    final_analysis=cycle_analysis,
                    final_optimization=cycle_optimization,
                    final_verification=cycle_verification,
                    final_security=cycle_security,
                    escalation_reasons=escalation_reasons,
                    review_required=True,
                ).to_dict()

            if cycle_verification.get("status") == "PASS" and cycle_security.get("status") == "PASS":
                cycles[-1].stop_reason = "pass"
                return RefinementResult(
                    status="PASS",
                    stop_reason="pass",
                    cycle_count=len(cycles),
                    cycles=cycles,
                    final_analysis=cycle_analysis,
                    final_optimization=cycle_optimization,
                    final_verification=cycle_verification,
                    final_security=cycle_security,
                ).to_dict()

            if candidate_score <= last_score and candidate_confidence <= last_confidence:
                escalation_reasons.append("No material improvement after refinement cycle.")
                final_analysis = cycle_analysis
                final_optimization = cycle_optimization
                final_verification = cycle_verification
                final_security = cycle_security
                cycles[-1].stop_reason = "no_material_improvement"
                return RefinementResult(
                    status="ESCALATE",
                    stop_reason="no_material_improvement",
                    cycle_count=len(cycles),
                    cycles=cycles,
                    final_analysis=final_analysis,
                    final_optimization=final_optimization,
                    final_verification=final_verification,
                    final_security=final_security,
                    escalation_reasons=escalation_reasons,
                    review_required=True,
                ).to_dict()

            last_score = candidate_score
            last_confidence = candidate_confidence
            final_analysis = cycle_analysis
            final_optimization = cycle_optimization
            final_verification = cycle_verification
            final_security = cycle_security

        escalation_reasons.append("Refinement exhausted the configured cycle limit.")
        return RefinementResult(
            status="ESCALATE",
            stop_reason="max_cycles_reached",
            cycle_count=len(cycles),
            cycles=cycles,
            final_analysis=final_analysis,
            final_optimization=final_optimization,
            final_verification=final_verification,
            final_security=final_security,
            escalation_reasons=escalation_reasons,
            review_required=True,
        ).to_dict()


def _merge_feedback_findings(
    analysis_report: Dict[str, Any],
    verification_report: Dict[str, Any],
    security_report: Dict[str, Any],
) -> Dict[str, Any]:
    merged = deepcopy(analysis_report)
    all_findings = list(merged.get("all_findings", []))

    diff_error = verification_report.get("diff_error")
    if diff_error:
        all_findings.append({
            "type": "verification_feedback",
            "description": f"Verification feedback: {diff_error}",
            "line": None,
            "severity": "high",
            "source": "refinement",
        })

    for finding in security_report.get("rollback_triggers", []) or []:
        all_findings.append({
            "type": finding.get("type", "security_feedback"),
            "description": finding.get("description", "Security rollback trigger."),
            "line": finding.get("line"),
            "severity": finding.get("severity", "high"),
            "source": "refinement",
        })

    merged["all_findings"] = all_findings
    return merged


def _score_from_reports(verification_report: Dict[str, Any], security_report: Dict[str, Any]) -> int:
    if security_report.get("status") == "ROLLBACK":
        return 0
    ver_status = verification_report.get("status")
    if ver_status == "PASS":
        return 3
    if ver_status == "FAIL":
        return 1
    if ver_status == "ROLLBACK":
        return 0
    return 1

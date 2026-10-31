"""
Top-level workflow coordinator for the full pipeline plus bounded refinement.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent_framework import BaseAgent, ContextManager
from src.pipeline.pipeline import CompilerOptimizationPipeline, PipelineResult
from src.temp_paths import runtime_temp_dir
from .refinement_agent import RefinementAgent

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    workflow_status: str
    pipeline_result: PipelineResult
    iteration_count: int = 0
    stop_reason: str = ""
    review_required: bool = False
    escalation_reasons: List[str] = field(default_factory=list)
    refinement: Dict[str, Any] = field(default_factory=dict)
    cache_hits: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_status": self.workflow_status,
            "iteration_count": self.iteration_count,
            "stop_reason": self.stop_reason,
            "review_required": self.review_required,
            "escalation_reasons": self.escalation_reasons,
            "refinement": self.refinement,
            "cache_hits": self.cache_hits,
            "pipeline_result": {
                "file_path": self.pipeline_result.file_path,
                "status": self.pipeline_result.status,
                "analysis_report": self.pipeline_result.analysis_report,
                "optimization_report": self.pipeline_result.optimization_report,
                "verification_report": self.pipeline_result.verification_report,
                "security_report": self.pipeline_result.security_report,
                "error": self.pipeline_result.error,
            },
        }


class OrchestratorAgent(BaseAgent):
    def __init__(self, agent_id: str, context_manager: ContextManager, llm_client=None, message_logger=None):
        self.llm = llm_client
        self._message_logger = message_logger
        super().__init__(agent_id, "orchestrator", context_manager)

    def get_capabilities(self) -> List[str]:
        return [
            "multi_agent_coordination",
            "refinement_triggering",
            "workflow_state_management",
            "escalation_decisioning",
        ]

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        file_path = input_data.get("file_path")
        source_code = input_data.get("source_code")
        low_conf_threshold = float(input_data.get("low_conf_threshold", 0.8))
        max_cycles = int(input_data.get("max_cycles", 3))

        temp_path: Optional[str] = None
        if not file_path and source_code:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".cpp", delete=False, encoding="utf-8", dir=runtime_temp_dir()
            ) as handle:
                handle.write(source_code)
                temp_path = handle.name
                file_path = temp_path

        if not file_path or not os.path.isfile(file_path):
            result = PipelineResult(
                file_path=file_path or "<unknown>",
                status="failed",
                error="File not found for orchestrated run.",
            )
            return OrchestrationResult(
                workflow_status="ABORTED",
                pipeline_result=result,
                stop_reason="missing_file",
                review_required=True,
                escalation_reasons=["Unable to resolve source file for orchestration."],
            ).to_dict()

        try:
            pipeline = CompilerOptimizationPipeline(
                llm_client=self.llm,
                message_logger=self._message_logger,
            )
            initial_result = pipeline.run(file_path)
            optimization_confidence = float(
                initial_result.optimization_report.get("confidence", 0.0)
            )
            review_reasons: List[str] = []

            if (
                initial_result.status == "success"
                and initial_result.verification_report.get("status") == "PASS"
                and initial_result.security_report.get("status") == "PASS"
                and optimization_confidence >= low_conf_threshold
            ):
                return OrchestrationResult(
                    workflow_status="PASS",
                    pipeline_result=initial_result,
                    stop_reason="initial_pass",
                    cache_hits=_collect_cache_hits(initial_result),
                ).to_dict()

            refinement_agent = RefinementAgent(
                "refinement_1",
                ContextManager(),
                self.llm,
            )
            with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
                original_code = handle.read()

            refinement = refinement_agent.process({
                "original_code": original_code,
                "file_path": file_path,
                "analysis_report": initial_result.analysis_report,
                "previous_optimization": initial_result.optimization_report,
                "previous_verification": initial_result.verification_report,
                "previous_security": initial_result.security_report,
                "low_conf_threshold": low_conf_threshold,
                "max_cycles": max_cycles,
            })

            if refinement.get("status") == "PASS":
                refined_result = PipelineResult(
                    file_path=file_path,
                    status="success",
                    analysis_report=refinement.get("final_analysis", {}),
                    optimization_report=refinement.get("final_optimization", {}),
                    verification_report=refinement.get("final_verification", {}),
                    security_report=refinement.get("final_security", {}),
                )
                return OrchestrationResult(
                    workflow_status="PASS",
                    pipeline_result=refined_result,
                    iteration_count=refinement.get("cycle_count", 0),
                    stop_reason=refinement.get("stop_reason", "refinement_pass"),
                    refinement=refinement,
                    cache_hits=_collect_cache_hits(refined_result),
                ).to_dict()

            review_reasons.extend(refinement.get("escalation_reasons", []))
            final_result = PipelineResult(
                file_path=file_path,
                status=initial_result.status,
                analysis_report=refinement.get("final_analysis", initial_result.analysis_report),
                optimization_report=refinement.get("final_optimization", initial_result.optimization_report),
                verification_report=refinement.get("final_verification", initial_result.verification_report),
                security_report=refinement.get("final_security", initial_result.security_report),
                error=initial_result.error,
            )
            workflow_status = refinement.get("status", "ESCALATE")
            if workflow_status not in {"ROLLBACK", "ESCALATE", "ABORTED"}:
                workflow_status = "ESCALATE"

            return OrchestrationResult(
                workflow_status=workflow_status,
                pipeline_result=final_result,
                iteration_count=refinement.get("cycle_count", 0),
                stop_reason=refinement.get("stop_reason", "escalated"),
                review_required=True,
                escalation_reasons=review_reasons,
                refinement=refinement,
                cache_hits=_collect_cache_hits(final_result),
            ).to_dict()
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass


def _collect_cache_hits(result: PipelineResult) -> Dict[str, bool]:
    return {
        "analysis": bool(result.analysis_report.get("cache_hit")),
        "optimization": bool(result.optimization_report.get("cache_hit")),
        "verification": bool(result.verification_report.get("cache_hit")),
        "security": bool(result.security_report.get("cache_hit")),
    }

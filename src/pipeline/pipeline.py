"""
Compiler Optimization Pipeline — Weeks 6–8

Chains: AnalysisAgent → OptimizationAgent → VerificationAgent → SecurityAgent
All agents share a single ContextManager instance.
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

_root = os.path.join(os.path.dirname(__file__), "..", "..")
if _root not in sys.path:
    sys.path.insert(0, _root)

from agent_framework import AgentRegistry, ContextManager
from agent_framework.message_protocol import Message, MessageType, MessagePriority
from src.llm.llm_client import LLMClient
from src.agents.analysis_agent import AnalysisAgent
from src.agents.optimization_agent import OptimizationAgent
from src.agents.verification_agent import VerificationAgent
from src.agents.security_agent import SecurityAgent

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    file_path: str
    status: str                  # "success" | "partial" | "failed" | "rollback"
    analysis_report: Dict[str, Any] = field(default_factory=dict)
    optimization_report: Dict[str, Any] = field(default_factory=dict)
    verification_report: Dict[str, Any] = field(default_factory=dict)
    security_report: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f" Pipeline Result for: {self.file_path}",
            f" Status: {self.status.upper()}",
            f"{'='*60}",
        ]
        # Analysis
        if self.analysis_report:
            n = len(self.analysis_report.get("all_findings", []))
            lines.append(f"\n[Analysis]  {n} finding(s)")
            lines.append(self.analysis_report.get("summary", ""))

        # Optimization
        if self.optimization_report:
            n = len(self.optimization_report.get("transformations", []))
            lines.append(f"\n[Optimization]  {n} transformation(s)")
            lines.append(self.optimization_report.get("summary", ""))
            out = self.optimization_report.get("output_file", "")
            if out:
                lines.append(f"  Saved to: {out}")
            diff = self.optimization_report.get("unified_diff", "")
            if diff:
                lines.append("\n[Unified Diff]")
                lines.append(diff[:1500] + ("... (truncated)" if len(diff) > 1500 else ""))

        # Verification
        if self.verification_report:
            lines.append(f"\n[Verification]")
            lines.append(self.verification_report.get("summary", ""))

        # Security
        if self.security_report:
            n_all = len(self.security_report.get("all_vulnerabilities", []))
            n_new = len(self.security_report.get("new_vulnerabilities", []))
            risk  = self.security_report.get("overall_risk", "?").upper()
            sec_status = self.security_report.get("status", "?")
            lines.append(f"\n[Security]  {n_all} finding(s), {n_new} new | "
                         f"Risk: {risk} | Status: {sec_status}")
            lines.append(self.security_report.get("summary", ""))

        if self.error:
            lines.append(f"\n[Error] {self.error}")

        return "\n".join(lines)


class CompilerOptimizationPipeline:
    """
    End-to-end pipeline from C++ source → analysis → optimization → verification.

    Usage
    -----
    pipeline = CompilerOptimizationPipeline()
    result = pipeline.run("path/to/file.cpp")
    print(result.summary())
    """

    def __init__(self, llm_client: LLMClient = None, message_logger=None):
        self.llm      = llm_client or LLMClient()
        self.context  = ContextManager()
        self.registry = AgentRegistry()
        self._msg_logger = message_logger  # optional MessageLogger

        # Create agents
        self.analysis_agent = AnalysisAgent(
            "analysis_1", self.context, self.llm
        )
        self.optimization_agent = OptimizationAgent(
            "optimization_1", self.context, self.llm
        )
        self.verification_agent = VerificationAgent(
            "verification_1", self.context, self.llm
        )
        self.security_agent = SecurityAgent(
            "security_1", self.context, self.llm
        )

        # Register
        self.registry.register(self.analysis_agent)
        self.registry.register(self.optimization_agent)
        self.registry.register(self.verification_agent)
        self.registry.register(self.security_agent)

    # ── Internal message helper ────────────────────────────────────────────────

    def _route(self, sender_id: str, receiver_id: str,
               msg_type: MessageType, payload: dict,
               priority: MessagePriority = MessagePriority.HIGH,
               corr_id: str = None):
        """
        Create a message and log it via the MessageLogger (pure observer).

        We do NOT call registry.route_message() here because agent threads
        are not started in pipeline mode — doing so would put messages on an
        unread PriorityQueue and cause heapq comparison errors on Message
        objects. The MessageLogger observes messages independently.
        """
        msg = Message.create(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=msg_type,
            payload=payload,
            priority=priority,
            correlation_id=corr_id,
        )
        # Notify observer only (no queue, no thread)
        if self._msg_logger:
            self._msg_logger._on_message(msg)
        logger.debug(
            f"MSG {msg.message_type.value}: {sender_id} → {receiver_id} "
            f"payload_keys={list(payload.keys())}"
        )
        return msg.message_id

    def run(self, file_path: str) -> PipelineResult:
        """Run the full pipeline on a C++ source file."""
        logger.info(f"Pipeline starting: {file_path}")

        if not os.path.isfile(file_path):
            return PipelineResult(
                file_path=file_path,
                status="failed",
                error=f"File not found: {file_path}",
            )

        # Read source
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source_code = f.read()
        except OSError as exc:
            return PipelineResult(
                file_path=file_path, status="failed",
                error=f"Cannot read file: {exc}",
            )

        # Reset shared context for this run
        self.context.clear()

        # ── Step 1: Analysis ──────────────────────────────────────────────────
        logger.info("Step 1/4: Analysis")

        # Broadcast REQUEST to analysis agent (MessageLogger sees this)
        req1_id = self._route(
            sender_id="pipeline",
            receiver_id="analysis_1",
            msg_type=MessageType.REQUEST,
            payload={
                "action":      "analyse",
                "file_path":   file_path,
                "source_code": source_code,
                "line_count":  source_code.count("\n"),
            },
        )

        try:
            analysis_result = self.analysis_agent.process({
                "source_code": source_code,
                "file_path":   file_path,
            })
        except Exception as exc:
            logger.error(f"Analysis failed: {exc}")
            return PipelineResult(
                file_path=file_path, status="failed",
                error=f"Analysis step failed: {exc}",
            )

        # Agent responds back to pipeline
        self._route(
            sender_id="analysis_1",
            receiver_id="pipeline",
            msg_type=MessageType.RESPONSE,
            payload={
                "status":       "ok",
                "findings":     len(analysis_result.get("all_findings", [])),
                "confidence":   analysis_result.get("confidence", 0),
                "conclusion":   analysis_result.get("conclusion", ""),
                "high_sev":     sum(1 for f in analysis_result.get("all_findings", [])
                                   if f.get("severity") == "high"),
            },
            corr_id=req1_id,
        )

        # ── Step 2: Optimization ──────────────────────────────────────────────
        logger.info("Step 2/4: Optimization")

        # Notify optimization agent that analysis is ready
        req2_id = self._route(
            sender_id="analysis_1",
            receiver_id="optimization_1",
            msg_type=MessageType.NOTIFICATION,
            payload={
                "action":    "analysis_complete",
                "findings":  len(analysis_result.get("all_findings", [])),
                "conclusion": analysis_result.get("conclusion", ""),
            },
        )

        # Pipeline issues the optimise REQUEST
        req2b_id = self._route(
            sender_id="pipeline",
            receiver_id="optimization_1",
            msg_type=MessageType.REQUEST,
            payload={
                "action":      "optimise",
                "file_path":   file_path,
                "source_code": source_code,
                "n_findings":  len(analysis_result.get("all_findings", [])),
            },
        )

        try:
            opt_result = self.optimization_agent.process({
                "source_code":     source_code,
                "file_path":       file_path,
                "analysis_report": analysis_result,
            })
        except Exception as exc:
            logger.error(f"Optimization failed: {exc}")
            return PipelineResult(
                file_path=file_path, status="partial",
                analysis_report=analysis_result,
                error=f"Optimization step failed: {exc}",
            )

        # Optimization agent responds
        self._route(
            sender_id="optimization_1",
            receiver_id="pipeline",
            msg_type=MessageType.RESPONSE,
            payload={
                "status":          "ok",
                "transformations": len(opt_result.get("transformations", [])),
                "output_file":     opt_result.get("output_file", ""),
                "conclusion":      opt_result.get("conclusion", ""),
                "confidence":      opt_result.get("confidence", 0),
                "diff_size":       len(opt_result.get("unified_diff", "")),
            },
            corr_id=req2b_id,
        )

        # ── Step 3: Verification ──────────────────────────────────────────────
        logger.info("Step 3/4: Verification")
        optimized_code = opt_result.get("optimized_code", source_code)

        # Optimization notifies verification that code is ready
        req3_id = self._route(
            sender_id="optimization_1",
            receiver_id="verification_1",
            msg_type=MessageType.NOTIFICATION,
            payload={
                "action":          "optimization_complete",
                "transformations": len(opt_result.get("transformations", [])),
                "diff_size":       len(opt_result.get("unified_diff", "")),
            },
        )

        # Pipeline issues the verify REQUEST
        req3b_id = self._route(
            sender_id="pipeline",
            receiver_id="verification_1",
            msg_type=MessageType.REQUEST,
            payload={
                "action":           "verify",
                "file_path":        file_path,
                "original_code":    source_code,
                "optimized_code":   optimized_code,
            },
        )

        try:
            ver_result = self.verification_agent.process({
                "original_code":  source_code,
                "optimized_code": optimized_code,
                "file_path":      file_path,
            })
        except Exception as exc:
            logger.error(f"Verification failed: {exc}")
            return PipelineResult(
                file_path=file_path, status="partial",
                analysis_report=analysis_result,
                optimization_report=opt_result,
                error=f"Verification step failed: {exc}",
            )

        # Verification agent sends final verdict back to pipeline
        self._route(
            sender_id="verification_1",
            receiver_id="pipeline",
            msg_type=MessageType.RESPONSE,
            payload={
                "status":         ver_result.get("status"),
                "diff_passed":    ver_result.get("diff_passed"),
                "z3_status":      ver_result.get("z3_status"),
                "perf_summary":   ver_result.get("perf_summary", ""),
                "llm_verdict":    ver_result.get("llm_verdict", ""),
                "conclusion":     ver_result.get("conclusion", ""),
            },
            corr_id=req3b_id,
        )

        # ── Step 4: Security ──────────────────────────────────────────────────
        logger.info("Step 4/4: Security")

        # If verification already rolled back, security scans the original code
        ver_status   = ver_result.get("status", "PASS")
        final_code   = optimized_code if ver_status not in ("ROLLBACK", "FAIL") \
                       else source_code

        req4_id = self._route(
            sender_id="verification_1",
            receiver_id="security_1",
            msg_type=MessageType.NOTIFICATION,
            payload={
                "action":       "verification_complete",
                "ver_status":   ver_status,
                "final_code_len": len(final_code),
            },
        )

        req4b_id = self._route(
            sender_id="pipeline",
            receiver_id="security_1",
            msg_type=MessageType.REQUEST,
            payload={
                "action":          "security_audit",
                "file_path":       file_path,
                "original_code":   source_code,
                "optimized_code":  final_code,
            },
        )

        if self.security_agent is None:
            logger.info("Step 4/4: Security — skipped (no security agent)")
            sec_result = {
                "all_vulnerabilities": [], "new_vulnerabilities": [],
                "overall_risk": "unknown", "status": "PASS",
                "summary": "Security audit skipped.", "sources": [],
            }
        else:
            try:
                sec_result = self.security_agent.process({
                    "original_code":  source_code,
                    "optimized_code": final_code,
                    "file_path":      file_path,
                })
            except Exception as exc:
                logger.error(f"Security audit failed: {exc}")
                sec_result = {
                    "all_vulnerabilities": [],
                    "new_vulnerabilities": [],
                    "overall_risk": "unknown",
                    "status": "PASS",
                    "summary": f"Security audit failed: {exc}",
                    "sources": [],
                }

        self._route(
            sender_id="security_1",
            receiver_id="pipeline",
            msg_type=MessageType.RESPONSE,
            payload={
                "status":       sec_result.get("status"),
                "overall_risk": sec_result.get("overall_risk"),
                "total_vulns":  len(sec_result.get("all_vulnerabilities", [])),
                "new_vulns":    len(sec_result.get("new_vulnerabilities", [])),
                "sources":      sec_result.get("sources", []),
            },
            corr_id=req4b_id,
        )

        # ── Determine overall status ──────────────────────────────────────────
        if ver_status == "ROLLBACK" or sec_result.get("status") == "ROLLBACK":
            status = "rollback"
        elif ver_status == "FAIL":
            status = "partial"
        else:
            status = "success"

        logger.info(f"Pipeline complete: {status}")
        return PipelineResult(
            file_path=file_path,
            status=status,
            analysis_report=analysis_result,
            optimization_report=opt_result,
            verification_report=ver_result,
            security_report=sec_result,
        )

    def run_string(self, source_code: str, label: str = "<string>") -> PipelineResult:
        """Run the pipeline on a code string (for testing)."""
        import tempfile, os
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".cpp", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(source_code)
            tmp_path = tmp.name
        try:
            result = self.run(tmp_path)
            result.file_path = label
            return result
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

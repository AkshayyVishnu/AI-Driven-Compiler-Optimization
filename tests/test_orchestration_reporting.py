"""
Deterministic unittest coverage for orchestration, reporting, and domain rules.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_framework import ContextManager
from src.agents.orchestrator_agent import OrchestratorAgent
from src.domains.domain_rules import apply_domain_optimizations, detect_domain_findings
from src.pipeline.pipeline import PipelineResult
from src.reporting.exporters import export_html_report, export_markdown_report
from src.reporting.report_contract import build_explainability_report


def _pipeline_result(status: str = "success", confidence: float = 0.92) -> PipelineResult:
    return PipelineResult(
        file_path="sample.cpp",
        status=status,
        analysis_report={
            "all_findings": [
                {
                    "type": "memory_buffer_copy_loop",
                    "description": "Copy loop detected.",
                    "severity": "medium",
                    "source": "domain",
                }
            ],
            "conclusion": "Rule-based analysis completed.",
            "cache_hit": False,
        },
        optimization_report={
            "optimized_code": "void f(){ memcpy(dst, src, n * sizeof(dst[0])); }",
            "transformations": [
                {
                    "type": "memory_buffer_copy_loop_to_memcpy",
                    "description": "Converted a copy loop to memcpy.",
                }
            ],
            "unified_diff": "--- a\n+++ b\n- dst[i] = src[i];\n+ memcpy(dst, src, n * sizeof(dst[0]));\n",
            "output_file": "MicroBenchmarks/Generated_optimisation/OPT_sample.cpp",
            "conclusion": "Applied deterministic rule-based transforms.",
            "confidence": confidence,
            "cache_hit": False,
        },
        verification_report={
            "status": "PASS",
            "summary": "Verification passed.",
            "conclusion": "Status: PASS.",
            "cache_hit": False,
        },
        security_report={
            "status": "PASS",
            "summary": "No new vulnerabilities introduced.",
            "overall_risk": "low",
            "all_vulnerabilities": [],
            "new_vulnerabilities": [],
            "cache_hit": False,
        },
    )


class TestDomainRules(unittest.TestCase):
    def test_memory_copy_loop_detection_and_transform(self):
        source = """
void copy_buf(int* dst, int* src, int n) {
    for (int i = 0; i < n; i++) { dst[i] = src[i]; }
}
"""
        findings = detect_domain_findings(source)
        self.assertTrue(any(item["type"] == "memory_buffer_copy_loop" for item in findings))

        optimized, transforms = apply_domain_optimizations(source)
        self.assertIn("memcpy(dst, src, n * sizeof(dst[0]))", optimized)
        self.assertTrue(
            any(item["type"] == "memory_buffer_copy_loop_to_memcpy" for item in transforms)
        )

    def test_scientific_numeric_reduction_detection(self):
        source = """
double sum(double* a, int n) {
    double acc = 0;
    for (int i = 0; i < n; i++) { acc += a[i]; }
    return acc;
}
"""
        findings = detect_domain_findings(source)
        self.assertTrue(
            any(item["type"] == "scientific_numeric_reduction" for item in findings)
        )


class TestOrchestrator(unittest.TestCase):
    def test_initial_success_returns_pass(self):
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".cpp",
            delete=False,
            dir=os.path.dirname(__file__),
            encoding="utf-8",
        ) as fh:
            fh.write("int main() { return 0; }\n")
            source_path = fh.name

        class FakePipeline:
            def __init__(self, llm_client=None, message_logger=None):
                pass

            def run(self, file_path):
                return _pipeline_result(status="success", confidence=0.95)

        try:
            with patch("src.agents.orchestrator_agent.CompilerOptimizationPipeline", FakePipeline):
                result = OrchestratorAgent("orch", ContextManager()).process(
                    {"file_path": source_path}
                )
        finally:
            os.unlink(source_path)

        self.assertEqual(result["workflow_status"], "PASS")
        self.assertEqual(result["stop_reason"], "initial_pass")
        self.assertEqual(result["iteration_count"], 0)

    def test_successful_refinement_promotes_to_pass(self):
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".cpp",
            delete=False,
            dir=os.path.dirname(__file__),
            encoding="utf-8",
        ) as fh:
            fh.write("int main() { return 0; }\n")
            source_path = fh.name

        class FakePipeline:
            def __init__(self, llm_client=None, message_logger=None):
                pass

            def run(self, file_path):
                result = _pipeline_result(status="rollback", confidence=0.3)
                result.verification_report["status"] = "ROLLBACK"
                return result

        refinement_payload = {
            "status": "PASS",
            "stop_reason": "pass",
            "cycle_count": 1,
            "final_analysis": _pipeline_result().analysis_report,
            "final_optimization": _pipeline_result().optimization_report,
            "final_verification": _pipeline_result().verification_report,
            "final_security": _pipeline_result().security_report,
            "escalation_reasons": [],
            "review_required": False,
        }

        try:
            with patch("src.agents.orchestrator_agent.CompilerOptimizationPipeline", FakePipeline):
                with patch(
                    "src.agents.orchestrator_agent.RefinementAgent.process",
                    return_value=refinement_payload,
                ):
                    result = OrchestratorAgent("orch", ContextManager()).process(
                        {"file_path": source_path}
                    )
        finally:
            os.unlink(source_path)

        self.assertEqual(result["workflow_status"], "PASS")
        self.assertEqual(result["iteration_count"], 1)
        self.assertEqual(result["pipeline_result"]["status"], "success")


class TestExplainabilityReporting(unittest.TestCase):
    def test_report_exports_are_consistent(self):
        pipeline_result = _pipeline_result()
        orchestration = {
            "workflow_status": "PASS",
            "iteration_count": 1,
            "stop_reason": "pass",
            "review_required": False,
            "escalation_reasons": [],
            "cache_hits": {
                "analysis": False,
                "optimization": False,
                "verification": False,
                "security": False,
            },
        }
        report = build_explainability_report("sample.cpp", pipeline_result, orchestration)

        markdown = export_markdown_report(report)
        html = export_html_report(report)

        self.assertIn("Explainability Report", markdown)
        self.assertIn("memory_buffer_copy_loop_to_memcpy", markdown)
        self.assertIn("<html", html.lower())
        self.assertIn("Workflow status", html)


if __name__ == "__main__":
    unittest.main()

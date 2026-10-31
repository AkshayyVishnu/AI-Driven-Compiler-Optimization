"""
Generate deterministic Week 13 evidence reports for the revised source-to-source scope.

Outputs:
- Complete_Test_Report.md
- Performance_Benchmark_Report.md
- Comparative_Analysis_Report.md
- week13_results.json
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.llm.llm_client import LLMClient
from src.pipeline.pipeline import CompilerOptimizationPipeline, PipelineResult

ROOT = os.path.join(os.path.dirname(__file__), "..")
TESTCASES_DIR = os.path.join(ROOT, "MicroBenchmarks", "Testcases")
OUT_DIR = os.path.join(ROOT, "Technical Deliverlables and Documents")
JSON_PATH = os.path.join(os.path.dirname(__file__), "week13_results.json")

EVAL_CASES = [
    ("TC01_uninit_arithmetic.cpp", "correctness", "Uninitialized variable"),
    ("TC07_div_by_zero_var.cpp", "correctness", "Division by zero"),
    ("TC11_buffer_overflow_loop.cpp", "security", "Buffer overflow loop"),
    ("TC12_strcpy_overflow.cpp", "security", "Unsafe strcpy"),
    ("TC14_memory_leak.cpp", "correctness", "Memory leak"),
    ("TC16_use_after_free.cpp", "rollback", "Use-after-free"),
    ("TC20_leak_in_loop.cpp", "correctness", "Leak in loop"),
    ("TC27_int_overflow.cpp", "security", "Integer overflow"),
    ("TC31_off_by_one.cpp", "correctness", "Off-by-one"),
    ("TC35_unreachable_code.cpp", "correctness", "Unreachable code"),
    ("TC39_empty_if_body.cpp", "correctness", "Empty if body"),
    ("TC41_leak_early_return.cpp", "correctness", "Leak on early return"),
]


@dataclass
class CaseReport:
    filename: str
    bucket: str
    description: str
    orchestrated_status: str
    workflow_status: str
    iteration_count: int
    stop_reason: str
    review_required: bool
    elapsed_s: float
    basic_status: str
    basic_elapsed_s: float
    analysis_findings: int
    transformations: int
    verification_status: str
    security_status: str
    new_vulns: int
    overall_risk: str
    stage_timings: Dict[str, Dict[str, float]] = field(default_factory=dict)


def _make_pipeline(no_llm: bool = True) -> CompilerOptimizationPipeline:
    llm = LLMClient()
    if no_llm:
        llm._available = False
    pipeline = CompilerOptimizationPipeline(llm_client=llm)
    if no_llm:
        for agent in (
            pipeline.analysis_agent,
            pipeline.optimization_agent,
            pipeline.verification_agent,
            pipeline.security_agent,
        ):
            if agent is not None:
                agent.llm._available = False
    return pipeline


def _to_pipeline_result(orchestration: Dict[str, Any], file_path: str) -> PipelineResult:
    payload = orchestration.get("pipeline_result", {})
    return PipelineResult(
        file_path=payload.get("file_path", file_path),
        status=payload.get("status", "failed"),
        analysis_report=payload.get("analysis_report", {}),
        optimization_report=payload.get("optimization_report", {}),
        verification_report=payload.get("verification_report", {}),
        security_report=payload.get("security_report", {}),
        error=payload.get("error"),
    )


def run_case(filename: str, bucket: str, description: str) -> CaseReport:
    file_path = os.path.join(TESTCASES_DIR, filename)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)

    orchestrated_pipeline = _make_pipeline(no_llm=True)
    t0 = time.perf_counter()
    orchestration = orchestrated_pipeline.run_orchestrated(file_path, max_cycles=3, low_conf_threshold=0.8)
    elapsed = round(time.perf_counter() - t0, 4)
    orchestrated_result = _to_pipeline_result(orchestration, file_path)

    basic_pipeline = _make_pipeline(no_llm=True)
    t1 = time.perf_counter()
    basic_result = basic_pipeline.run(file_path)
    basic_elapsed = round(time.perf_counter() - t1, 4)

    return CaseReport(
        filename=filename,
        bucket=bucket,
        description=description,
        orchestrated_status=orchestrated_result.status,
        workflow_status=orchestration.get("workflow_status", "UNKNOWN"),
        iteration_count=orchestration.get("iteration_count", 0),
        stop_reason=orchestration.get("stop_reason", ""),
        review_required=bool(orchestration.get("review_required", False)),
        elapsed_s=elapsed,
        basic_status=basic_result.status,
        basic_elapsed_s=basic_elapsed,
        analysis_findings=len(orchestrated_result.analysis_report.get("all_findings", [])),
        transformations=len(orchestrated_result.optimization_report.get("transformations", [])),
        verification_status=orchestrated_result.verification_report.get("status", "UNKNOWN"),
        security_status=orchestrated_result.security_report.get("status", "UNKNOWN"),
        new_vulns=len(orchestrated_result.security_report.get("new_vulnerabilities", [])),
        overall_risk=orchestrated_result.security_report.get("overall_risk", "unknown"),
        stage_timings={
            "analysis": orchestrated_result.analysis_report.get("stage_timings", {}),
            "optimization": orchestrated_result.optimization_report.get("stage_timings", {}),
            "verification": orchestrated_result.verification_report.get("stage_timings", {}),
            "security": orchestrated_result.security_report.get("stage_timings", {}),
        },
    )


def build_complete_test_report(reports: List[CaseReport]) -> str:
    passes = sum(1 for item in reports if item.workflow_status == "PASS")
    rollbacks = sum(1 for item in reports if item.workflow_status == "ROLLBACK")
    escalations = sum(1 for item in reports if item.workflow_status == "ESCALATE")
    new_vulns = sum(item.new_vulns for item in reports)
    correctness_rate = round((passes / len(reports)) * 100, 1) if reports else 0.0

    lines = [
        "# Complete Test Report",
        "",
        f"**Generated:** {datetime.now(UTC).isoformat().replace('+00:00', 'Z')}  ",
        "**Evaluation mode:** deterministic rule-based (`--no-llm`)  ",
        "",
        "## Summary",
        "",
        f"- Cases executed: **{len(reports)}**",
        f"- Workflow PASS: **{passes}**",
        f"- Workflow ROLLBACK: **{rollbacks}**",
        f"- Workflow ESCALATE: **{escalations}**",
        f"- New vulnerabilities introduced: **{new_vulns}**",
        f"- Correctness-style pass rate: **{correctness_rate}%**",
        "",
        "## Per-Case Results",
        "",
        "| File | Bucket | Workflow | Iterations | Verification | Security | New Vulns | Risk |",
        "|------|--------|----------|------------|--------------|----------|-----------|------|",
    ]
    for item in reports:
        lines.append(
            f"| `{item.filename}` | {item.bucket} | {item.workflow_status} | "
            f"{item.iteration_count} | {item.verification_status} | {item.security_status} | "
            f"{item.new_vulns} | {item.overall_risk} |"
        )
    lines.extend([
        "",
        "## Acceptance Check",
        "",
        f"- Clean/safe outcomes are represented by the **{passes}** PASS cases.",
        f"- Rollback behavior is represented by the **{rollbacks}** rollback cases.",
        f"- Security regression count from measured runs is **{new_vulns}**.",
    ])
    return "\n".join(lines)


def build_performance_report(reports: List[CaseReport]) -> str:
    orchestrated_times = [item.elapsed_s for item in reports]
    basic_times = [item.basic_elapsed_s for item in reports]

    def avg(values: List[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    analysis_parse = avg([item.stage_timings["analysis"].get("parse_s", 0.0) for item in reports])
    analysis_rule = avg([item.stage_timings["analysis"].get("rule_s", 0.0) for item in reports])
    optimization_rule = avg([item.stage_timings["optimization"].get("rule_s", 0.0) for item in reports])
    verification_parallel = avg([item.stage_timings["verification"].get("parallel_checks_s", 0.0) for item in reports])
    security_total = avg([item.stage_timings["security"].get("total_s", 0.0) for item in reports])

    lines = [
        "# Performance Benchmark Report",
        "",
        f"**Generated:** {datetime.now(UTC).isoformat().replace('+00:00', 'Z')}  ",
        "**Evaluation mode:** deterministic rule-based (`--no-llm`)  ",
        "",
        "## End-to-End Latency",
        "",
        f"- Average orchestrated latency: **{avg(orchestrated_times)} s**",
        f"- Median orchestrated latency: **{round(statistics.median(orchestrated_times), 4)} s**",
        f"- Average baseline-pipeline latency: **{avg(basic_times)} s**",
        "",
        "## Average Stage Timings",
        "",
        f"- Analysis parse: **{analysis_parse} s**",
        f"- Analysis rule checks: **{analysis_rule} s**",
        f"- Optimization rule transforms: **{optimization_rule} s**",
        f"- Verification parallel checks: **{verification_parallel} s**",
        f"- Security total scan time: **{security_total} s**",
        "",
        "## Notes",
        "",
        "- These timings are measured from deterministic rule-based runs only.",
        "- Optional LLM timing is intentionally excluded from formal evaluation.",
    ]
    return "\n".join(lines)


def build_comparative_report(reports: List[CaseReport]) -> str:
    orchestrated_pass = sum(1 for item in reports if item.workflow_status == "PASS")
    baseline_success = sum(1 for item in reports if item.basic_status == "success")
    improved = sum(1 for item in reports if item.workflow_status == "PASS" and item.basic_status != "success")
    avg_delta = round(sum(item.basic_elapsed_s - item.elapsed_s for item in reports) / len(reports), 4)

    lines = [
        "# Comparative Analysis Report",
        "",
        f"**Generated:** {datetime.now(UTC).isoformat().replace('+00:00', 'Z')}  ",
        "",
        "## Compared Variants",
        "",
        "- Original baseline 4-stage pipeline",
        "- Revised orchestrated deterministic workflow",
        "",
        "## Aggregate Comparison",
        "",
        f"- Baseline `success` count: **{baseline_success}** / {len(reports)}",
        f"- Orchestrated `PASS` workflow count: **{orchestrated_pass}** / {len(reports)}",
        f"- Cases improved by orchestration/refinement: **{improved}**",
        f"- Average latency delta (`baseline - orchestrated`): **{avg_delta} s**",
        "",
        "## Case-by-Case Comparison",
        "",
        "| File | Baseline Status | Orchestrated Workflow | Delta (s) | Stop Reason |",
        "|------|------------------|-----------------------|-----------|-------------|",
    ]
    for item in reports:
        delta = round(item.basic_elapsed_s - item.elapsed_s, 4)
        lines.append(
            f"| `{item.filename}` | {item.basic_status} | {item.workflow_status} | "
            f"{delta} | {item.stop_reason or 'n/a'} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- The orchestrated workflow adds explicit bounded refinement and escalation metadata.",
        "- Comparisons here stay within the revised project scope: source-to-source workflow only.",
        "- No compiler baseline or LLM-only baseline is used in this formal report set.",
    ])
    return "\n".join(lines)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    reports = [run_case(filename, bucket, description) for filename, bucket, description in EVAL_CASES]

    with open(JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump([asdict(item) for item in reports], fh, indent=2)

    outputs = {
        os.path.join(OUT_DIR, "Complete_Test_Report.md"): build_complete_test_report(reports),
        os.path.join(OUT_DIR, "Performance_Benchmark_Report.md"): build_performance_report(reports),
        os.path.join(OUT_DIR, "Comparative_Analysis_Report.md"): build_comparative_report(reports),
    }

    for path, content in outputs.items():
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    print("Generated Week 13 deterministic reports:")
    for path in outputs:
        print(f" - {path}")
    print(f" - {JSON_PATH}")


if __name__ == "__main__":
    main()

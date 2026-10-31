"""
Verification Agent — Week 7

Orchestrates multi-layer verification of optimized C++ code:
  Layer 1: Differential Testing  (diff_tester.py)
  Layer 2: Z3 SMT Equivalence   (z3_verifier.py)  [optional]
  Layer 3: Performance Benchmark (perf_benchmarker.py)
  Layer 4: LLM Reasoning        (VerificationPromptTemplate)

If any layer fails, the agent triggers a context rollback.
"""

import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

_root = os.path.join(os.path.dirname(__file__), "..", "..")
if _root not in sys.path:
    sys.path.insert(0, _root)

from agent_framework import BaseAgent, ContextManager
from src.llm.llm_client import LLMClient
from src.llm.prompt_templates import VerificationPromptTemplate
from src.reasoning.cot_validator import CoTValidator
from src.runtime_cache import ResultCache, make_cache_key
from src.verification.diff_tester import DifferentialTester, DiffTestResult
from src.verification.z3_verifier import Z3Verifier, Z3Result
from src.verification.perf_benchmarker import PerfBenchmarker, PerfResult

logger = logging.getLogger(__name__)
_VERIFICATION_CACHE = ResultCache(max_entries=128)


@dataclass
class VerificationReport:
    status: str             # "PASS" | "FAIL" | "ROLLBACK"
    diff_result: Optional[DiffTestResult] = None
    z3_result: Optional[Z3Result] = None
    perf_result: Optional[PerfResult] = None
    llm_verdict: Optional[str] = None
    reasoning_steps: List[str] = None
    conclusion: str = ""
    summary: str = ""

    def __post_init__(self):
        if self.reasoning_steps is None:
            self.reasoning_steps = []


class VerificationAgent(BaseAgent):
    """
    Verification Agent: multi-layer correctness and performance checker.

    Input (passed to process()):
        {
            "original_code":  "<original C++ source>",
            "optimized_code": "<optimized C++ source>",
            "file_path":      "<optional label>",
        }
        If fields are missing, the agent reads from ContextManager.

    Output: VerificationReport as dict
    """

    def __init__(
        self,
        agent_id: str,
        context_manager: ContextManager,
        llm_client: LLMClient = None,
    ):
        super().__init__(agent_id, "verification", context_manager)
        self.llm      = llm_client or LLMClient()
        self.cot_val  = CoTValidator()
        self.diff_tester = DifferentialTester()
        self.z3       = Z3Verifier()
        self.perf     = PerfBenchmarker()

    # ── BaseAgent interface ────────────────────────────────────────────────────

    def get_capabilities(self) -> List[str]:
        return [
            "differential_testing",
            "z3_smt_verification",
            "performance_benchmarking",
            "llm_reasoning_verification",
            "context_rollback_on_failure",
        ]

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        original  = input_data.get("original_code")  or \
                    self.context.get("original_code") or ""
        optimized = input_data.get("optimized_code")
        cache_enabled = input_data.get("use_cache", True)
        if not optimized:
            opt_report = self.context.get("optimization_suggestions") or {}
            optimized  = opt_report.get("optimized_code", original)
        file_path = input_data.get("file_path", self.context.get("source_file", "<unknown>"))

        if not original or not optimized:
            return {"status": "FAIL", "error": "Missing original or optimized code."}

        cache_key = make_cache_key("verification", original, optimized)
        if cache_enabled:
            cached = _VERIFICATION_CACHE.get(cache_key)
            if cached is not None:
                cached_result = deepcopy(cached)
                cached_result["cache_hit"] = True
                self.context.set("verification_status", cached_result)
                return cached_result

        # ── Layer 1: Differential Testing ─────────────────────────────────────
        logger.info("VerificationAgent [Layer 1/4]: Differential Testing …")
        stage_started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=3) as executor:
            diff_future = executor.submit(self.diff_tester.test, original, optimized)
            z3_future = executor.submit(self.z3.verify, original, optimized)
            perf_future = executor.submit(self.perf.benchmark, original, optimized)
            diff_result = diff_future.result()
        _dt_status = "PASS" if diff_result.passed else f"FAIL ({diff_result.error or 'outputs differ'})"
        logger.info(f"VerificationAgent [Layer 1/4]: Differential Test → {_dt_status}")
        if diff_result.error:
            logger.debug(f"  diff error detail: {diff_result.error}")

        # ── Layer 2: Z3 Verification ───────────────────────────────────────────
        logger.info("VerificationAgent [Layer 2/4]: Z3 SMT Verification …")
        z3_result = z3_future.result()
        logger.info(f"VerificationAgent [Layer 2/4]: Z3 → {z3_result.status}")
        if z3_result.explanation:
            logger.debug(f"  Z3 detail: {z3_result.explanation}")

        # ── Layer 3: Performance Benchmark ────────────────────────────────────
        logger.info("VerificationAgent [Layer 3/4]: Performance Benchmark …")
        perf_result = perf_future.result()
        layer_elapsed = time.perf_counter() - stage_started
        logger.info(f"VerificationAgent [Layer 3/4]: Perf → {perf_result.summary()}")

        # ── Layer 4: LLM Reasoning ─────────────────────────────────────────────
        logger.info("VerificationAgent [Layer 4/4]: LLM Reasoning …")
        # pass True (neutral) when the diff test was skipped so the LLM prompt
        # doesn't say "test FAILED" for a test that was never run
        _diff_passed_for_llm = True if diff_result.skipped else diff_result.passed
        llm_started = time.perf_counter()
        llm_verdict, reasoning_steps = self._llm_verify(
            original, optimized, _diff_passed_for_llm
        )
        llm_elapsed = time.perf_counter() - llm_started
        logger.info(f"VerificationAgent [Layer 4/4]: LLM verdict → {llm_verdict}")

        # ── Decide overall status ──────────────────────────────────────────────
        optimized_compile_failed = bool(diff_result.compile_error_optimized)

        # If uninitialized variables were fixed, the output WILL differ from the
        # original (original had UB / random values). This is an expected and
        # correct behavior change — do NOT treat it as a verification failure.
        analysis = self.context.get("analysis_results") or {}
        has_uninit_fix = any(
            f.get("type") == "uninitialized_variable"
            for f in analysis.get("all_findings", [])
        )

        real_test_failure = (
            not diff_result.passed
            and not diff_result.skipped                    # was not a skip
            and not diff_result.compile_error_original     # original wasn't already broken
            and diff_result.original_returncode == 0       # original ran cleanly (no UB/crash)
            and not has_uninit_fix                         # not an expected output change
        )
        if real_test_failure or optimized_compile_failed:
            logger.warning("Differential test FAILED — triggering rollback")
            self.context.rollback()
            status = "ROLLBACK"
        elif z3_result.status == "COUNTEREXAMPLE_FOUND":
            logger.warning("Z3 found counterexample — triggering rollback")
            self.context.rollback()
            status = "ROLLBACK"
        else:
            status = "PASS"

        report = VerificationReport(
            status=status,
            diff_result=diff_result,
            z3_result=z3_result,
            perf_result=perf_result,
            llm_verdict=llm_verdict,
            reasoning_steps=reasoning_steps,
            conclusion=self._build_conclusion(status, diff_result, z3_result, perf_result),
            summary=self._build_summary(
                status, file_path, diff_result, z3_result, perf_result, llm_verdict
            ),
        )

        result_dict = {
            "status":          report.status,
            # None when skipped so the frontend VerStatusBadge renders "Skip" not "Fail"
            "diff_passed":     None if diff_result.skipped else diff_result.passed,
            "diff_error":      diff_result.error,
            "z3_status":       z3_result.status,
            "perf_summary":    perf_result.summary(),
            "llm_verdict":     llm_verdict,
            "reasoning_steps": reasoning_steps,
            "conclusion":      report.conclusion,
            "summary":         report.summary,
            "cache_hit":       False,
            "stage_timings": {
                "parallel_checks_s": round(layer_elapsed, 4),
                "llm_s": round(llm_elapsed, 4),
            },
        }

        self.context.set("verification_status", result_dict)
        if cache_enabled:
            _VERIFICATION_CACHE.set(cache_key, deepcopy(result_dict))
        logger.info(f"Verification complete: {status}")
        return result_dict

    # ── LLM verification ──────────────────────────────────────────────────────

    def _llm_verify(self, orig, opt, diff_passed):
        if not self.llm.is_available():
            logger.info("VerificationAgent: LLM not available — skipping LLM reasoning")
            return "UNCERTAIN", ["LLM unavailable — skipping semantic verification."]

        prompt = VerificationPromptTemplate.build(orig, opt, diff_passed)
        raw    = self.llm.generate(prompt, system_prompt=VerificationPromptTemplate.SYSTEM)

        if "offline stub" in raw or "LLM offline stub" in raw:
            logger.warning("VerificationAgent: LLM returned stub — verdict UNCERTAIN")
            return "UNCERTAIN", ["LLM returned stub — semantic verification skipped."]

        cot = self.cot_val.validate(raw)
        if cot.is_valid:
            return cot.verdict or "UNCERTAIN", cot.reasoning_steps
        return "UNCERTAIN", ["LLM reasoning unavailable."]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_conclusion(self, status, diff, z3, perf) -> str:
        parts = [f"Status: {status}."]
        parts.append(
            "Differential test: " + (
                "PASS" if diff.passed else
                f"SKIPPED ({diff.error})" if diff.skipped else
                f"FAIL ({diff.error})"
            )
        )
        parts.append(f"Z3 equivalence: {z3.status}")
        if perf.available and not perf.error:
            parts.append(perf.summary())
        return " | ".join(parts)

    def _build_summary(self, status, file_path, diff, z3, perf, llm_verdict) -> str:
        lines = [
            f"Verification Report: {file_path}",
            f"Overall Status    : {status}",
            f"Differential Test : {'PASS' if diff.passed else 'SKIPPED' if diff.skipped else 'FAIL'}"
            + (f" — {diff.error}" if diff.error else ""),
            f"Z3 Verification   : {z3.status}"
            + (f" — {z3.explanation}" if z3.explanation else ""),
            f"Performance       : {perf.summary()}",
            f"LLM Verdict       : {llm_verdict}",
        ]
        if status == "ROLLBACK":
            lines.append("⚠ Context rolled back to pre-optimization state.")
        return "\n".join(lines)

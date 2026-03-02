"""
Optimization Agent — Week 6

Transforms C/C++ code to fix detected issues and improve performance.
Uses a hybrid approach:
  1. Rule-based auto-fixes (always work offline)
  2. LLM-generated optimizations (when Ollama is available)

Saves output to MicroBenchmarks/Generated_optimisation/
"""

import difflib
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import sys
_root = os.path.join(os.path.dirname(__file__), "..", "..")
if _root not in sys.path:
    sys.path.insert(0, _root)

from agent_framework import BaseAgent, ContextManager
from src.llm.llm_client import LLMClient
from src.llm.prompt_templates import OptimizationPromptTemplate
from src.reasoning.cot_validator import CoTValidator

logger = logging.getLogger(__name__)

# Where optimized files get saved
_OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MicroBenchmarks", "Generated_optimisation"
)


class OptimizationAgent(BaseAgent):
    """
    Optimization Agent: fixes bugs and improves performance of C/C++ code.

    Input  (passed to process()):
        {
            "source_code":     "<C++ source string>",
            "file_path":       "<optional original path>",
            "analysis_report": {<output from AnalysisAgent>}   # optional
        }

    Output:
        {
            "file_path":        str,
            "original_code":    str,
            "optimized_code":   str,
            "unified_diff":     str,
            "transformations":  [...],
            "reasoning_steps":  [...],
            "conclusion":       str,
            "confidence":       float,
            "output_file":      str,    # path where file was saved
            "summary":          str,
        }
    """

    def __init__(self, agent_id: str, context_manager: ContextManager,
                 llm_client: LLMClient = None, output_dir: str = _OUTPUT_DIR):
        super().__init__(agent_id, "optimization", context_manager)
        self.llm        = llm_client or LLMClient()
        self.cot_val    = CoTValidator()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ── BaseAgent interface ────────────────────────────────────────────────────

    def get_capabilities(self) -> List[str]:
        return [
            "off_by_one_fix",
            "uninitialized_variable_fix",
            "loop_bound_correction",
            "algorithm_replacement_suggestion",
            "diff_generation",
            "llm_code_transformation",
        ]

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        source_code     = input_data.get("source_code", "")
        file_path       = input_data.get("file_path", "<unknown>")
        analysis_report = input_data.get("analysis_report") or \
                          self.context.get("analysis_results") or {}

        if not source_code:
            logger.error("OptimizationAgent: no source_code provided")
            return {"error": "No source_code provided"}

        logger.info(f"OptimizationAgent: optimising '{os.path.basename(file_path)}'")
        n_findings = len(analysis_report.get('all_findings', []))
        logger.info(f"OptimizationAgent: {n_findings} finding(s) from analysis to address")

        # 1. Rule-based fixes
        logger.info("OptimizationAgent: applying rule-based fixes …")
        rule_code, rule_transforms = self._rule_based_fix(source_code, analysis_report)

        logger.info(f"OptimizationAgent: {len(rule_transforms)} rule-based fix(es) applied")
        for t in rule_transforms:
            logger.debug(f"  → {t.get('type')}: {t.get('description')}")

        # 2. LLM transforms
        logger.info("OptimizationAgent: calling LLM for additional transforms …")
        llm_code, llm_transforms, reasoning_steps, conclusion, confidence = \
            self._llm_optimize(source_code, analysis_report)
        logger.info(f"OptimizationAgent: LLM produced "
                    f"{'new code' if (llm_code and llm_code != source_code) else 'no change'} "
                    f"+ {len(llm_transforms)} transform(s)")

        # 3. Choose best code: prefer LLM if it produced different code, else rule-based
        if llm_code and llm_code != source_code:
            final_code   = llm_code
            all_transforms = rule_transforms + llm_transforms
        else:
            final_code   = rule_code
            all_transforms = rule_transforms

        # 4. Build unified diff
        diff = self._make_diff(source_code, final_code, file_path)

        # 5. Save to disk
        output_file = self._save_output(final_code, file_path)

        result = {
            "file_path":       file_path,
            "original_code":   source_code,
            "optimized_code":  final_code,
            "unified_diff":    diff,
            "transformations": all_transforms,
            "reasoning_steps": reasoning_steps,
            "conclusion":      conclusion,
            "confidence":      confidence,
            "output_file":     output_file,
            "summary":         self._build_summary(
                file_path, all_transforms, conclusion, diff
            ),
        }

        # Store in shared context
        self.context.set("optimization_suggestions", result)

        logger.info(
            f"Optimization complete: {len(all_transforms)} transforms, "
            f"saved to {output_file}"
        )
        return result

    # ── Rule-based fixes ──────────────────────────────────────────────────────

    def _rule_based_fix(
        self, src: str, analysis_report: Dict
    ) -> Tuple[str, List[Dict]]:
        code   = src
        transforms: List[Dict] = []
        findings = analysis_report.get("all_findings", []) or \
                   analysis_report.get("rule_findings", [])

        for finding in findings:
            ftype = finding.get("type", "")

            # Fix off-by-one: `i <= N` → `i < N`  in for-loop conditions
            if ftype in ("off_by_one_error", "potential_buffer_overflow"):
                fixed, change = self._fix_off_by_one(code)
                if change:
                    code = fixed
                    transforms.append({
                        "type":        "off_by_one_fix",
                        "description": "Changed '<=' to '<' in loop condition to prevent buffer overflow.",
                        "severity":    "info",
                    })

            # Fix uninitialized variable: add = 0
            if ftype == "uninitialized_variable":
                var = self._extract_varname(finding.get("description", ""))
                if var:
                    fixed, change = self._fix_uninit_var(code, var)
                    if change:
                        code = fixed
                        transforms.append({
                            "type":        "initialize_variable",
                            "description": f"Initialized variable '{var}' to 0.",
                            "severity":    "info",
                        })

        return code, transforms

    def _fix_off_by_one(self, src: str) -> Tuple[str, bool]:
        """Replace `<= <integer>` in `for(...)` conditions → `< <integer>`."""
        pattern = re.compile(
            r'(for\s*\([^;]*;\s*\w+\s*)<=(\s*\d+)',
            re.MULTILINE,
        )
        new_src, n = pattern.subn(lambda m: m.group(1) + "<" + m.group(2), src)
        return new_src, n > 0

    def _fix_uninit_var(self, src: str, varname: str) -> Tuple[str, bool]:
        """Add `= 0` to a bare variable declaration."""
        pattern = re.compile(
            r'(\b(?:int|float|double|char|long|short|unsigned|bool)\s+'
            + re.escape(varname) + r')\s*;'
        )
        new_src, n = pattern.subn(r'\g<1> = 0;', src)
        return new_src, n > 0

    def _extract_varname(self, description: str) -> Optional[str]:
        m = re.search(r"Variable '(\w+)'", description)
        return m.group(1) if m else None

    # ── LLM optimization ──────────────────────────────────────────────────────

    def _llm_optimize(
        self, src: str, analysis_report: Dict
    ) -> Tuple[Optional[str], List[Dict], List[str], str, float]:
        prompt = OptimizationPromptTemplate.build(src, analysis_report)
        raw    = self.llm.generate(
            prompt, system_prompt=OptimizationPromptTemplate.SYSTEM
        )
        cot = self.cot_val.validate(raw)
        if cot.is_valid and cot.optimized_code:
            return (
                cot.optimized_code,
                cot.findings,
                cot.reasoning_steps,
                cot.conclusion,
                cot.confidence,
            )
        logger.warning(f"LLM optimization CoT invalid or no code: {cot.error}")
        return None, [], ["Rule-based optimization only."], "Applied rule-based fixes.", 0.6

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _make_diff(self, original: str, optimized: str, file_path: str) -> str:
        orig_lines = original.splitlines(keepends=True)
        opt_lines  = optimized.splitlines(keepends=True)
        diff       = difflib.unified_diff(
            orig_lines, opt_lines,
            fromfile=f"original/{os.path.basename(file_path)}",
            tofile=f"optimized/{os.path.basename(file_path)}",
            lineterm="",
        )
        return "".join(diff)

    def _save_output(self, code: str, file_path: str) -> str:
        base     = os.path.basename(file_path) if file_path != "<unknown>" else "output.cpp"
        out_name = "OPT_" + base
        out_path = os.path.join(self.output_dir, out_name)
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(code)
            logger.info(f"Saved optimized code to {out_path}")
        except OSError as exc:
            logger.error(f"Could not save optimized file: {exc}")
        return out_path

    def _build_summary(
        self, file_path, transforms, conclusion, diff
    ) -> str:
        diff_lines = diff.count("\n+") + diff.count("\n-")
        lines = [
            f"Optimization Report: {file_path}",
            f"Transformations    : {len(transforms)}",
            f"Diff lines changed : ~{diff_lines}",
            f"Conclusion         : {conclusion}",
        ]
        for i, t in enumerate(transforms, 1):
            lines.append(f"  {i}. {t.get('type')}: {t.get('description')}")
        return "\n".join(lines)

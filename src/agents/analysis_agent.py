"""
Analysis Agent — Week 6

Detects bugs, performance issues, and security vulnerabilities in C/C++ code.
Uses a hybrid approach:
  1. Rule-based pattern matching (always works, no LLM required)
  2. LLM reasoning via Qwen 2.5 Coder (enriches results when online)
"""

import logging
import os
import re
from typing import Any, Dict, List

# Add project root to sys.path if needed
import sys
_root = os.path.join(os.path.dirname(__file__), "..", "..")
if _root not in sys.path:
    sys.path.insert(0, _root)

from agent_framework import BaseAgent, ContextManager
from src.llm.llm_client import LLMClient
from src.llm.prompt_templates import AnalysisPromptTemplate
from src.parser.code_parser import CodeParser
from src.reasoning.cot_validator import CoTValidator

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """
    Analysis Agent: detects code issues in C/C++ source files.

    Input  (passed to process()):
        {
            "source_code": "<C++ source as string>",
            "file_path":   "<optional path for labelling>"
        }

    Output:
        {
            "file_path":        str,
            "rule_findings":    [...],   # always populated
            "llm_findings":     [...],   # populated if LLM online
            "all_findings":     [...],   # merged, deduplicated
            "reasoning_steps":  [...],
            "conclusion":       str,
            "confidence":       float,
            "summary":          str,     # text for display
        }
    """

    def __init__(self, agent_id: str, context_manager: ContextManager,
                 llm_client: LLMClient = None):
        super().__init__(agent_id, "analysis", context_manager)
        self.llm     = llm_client or LLMClient()
        self.parser  = CodeParser()
        self.cot_val = CoTValidator()

    # ── BaseAgent interface ────────────────────────────────────────────────────

    def get_capabilities(self) -> List[str]:
        return [
            "uninitialized_variable_detection",
            "buffer_overflow_detection",
            "nested_loop_detection",
            "memory_leak_detection",
            "division_by_zero_detection",
            "llm_severity_classification",
        ]

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point called by the base agent framework."""
        source_code = input_data.get("source_code", "")
        file_path   = input_data.get("file_path", "<unknown>")

        if not source_code:
            logger.error("AnalysisAgent: no source_code provided")
            return {"error": "No source_code provided", "all_findings": []}

        logger.info(f"AnalysisAgent: parsing '{os.path.basename(file_path)}' "
                    f"({len(source_code)} chars)")
        # 1. Parse
        parse_result = self.parser.parse_string(source_code, file_path)

        logger.debug(f"AnalysisAgent: parse done — {parse_result.line_count} lines, "
                     f"{len(parse_result.functions)} function(s), "
                     f"max loop depth={parse_result.max_loop_depth}")

        # 2. Rule-based findings (offline-capable)
        logger.info("AnalysisAgent: running rule-based checks …")
        rule_findings = self._rule_based_analysis(parse_result, source_code)
        logger.info(f"AnalysisAgent: rule-based → {len(rule_findings)} finding(s)")

        # 3. LLM-based findings (enriches when online)
        logger.info("AnalysisAgent: calling LLM for enrichment …")
        llm_findings, reasoning_steps, conclusion, confidence = \
            self._llm_analysis(source_code, file_path, parse_result, rule_findings)

        logger.info(f"AnalysisAgent: LLM returned {len(llm_findings)} additional finding(s) "
                     f"(confidence={confidence:.2f})")

        # 4. Merge
        all_findings = self._merge_findings(rule_findings, llm_findings)
        logger.info(f"AnalysisAgent: merged total = {len(all_findings)} finding(s)")

        result = {
            "file_path":       file_path,
            "rule_findings":   rule_findings,
            "llm_findings":    llm_findings,
            "all_findings":    all_findings,
            "reasoning_steps": reasoning_steps,
            "conclusion":      conclusion,
            "confidence":      confidence,
            "summary":         self._build_summary(file_path, all_findings, conclusion),
            "parse_meta": {
                "line_count":      parse_result.line_count,
                "functions":       [f.name for f in parse_result.functions],
                "has_nested_loops": parse_result.has_nested_loops,
                "max_loop_depth":  parse_result.max_loop_depth,
            },
        }

        # Store in shared context
        self.context.set("analysis_results", result)
        self.context.set("original_code", source_code)
        self.context.set("source_file", file_path)

        logger.info(f"Analysis complete: {len(all_findings)} findings in {file_path}")
        return result

    # ── Rule-based analysis ───────────────────────────────────────────────────

    def _rule_based_analysis(self, parse_result, source_code: str) -> List[Dict]:
        findings = []

        # Uninitialized variables
        for v in parse_result.uninitialized_vars:
            findings.append({
                "type":        "uninitialized_variable",
                "description": (
                    f"Variable '{v['variable']}' declared at line "
                    f"{v['declared_line']} may be used before initialization."
                ),
                "line":        v["declared_line"],
                "severity":    "high",
                "source":      "rule",
            })

        # Buffer overflow heuristic: array[N] accessed with <= N in loop
        if parse_result.has_nested_loops or parse_result.loops:
            for acc in parse_result.array_accesses:
                if acc.get("is_var_index"):
                    findings.append({
                        "type":        "potential_buffer_overflow",
                        "description": (
                            f"Array '{acc['array']}' accessed with variable index "
                            f"'{acc['index']}' at line {acc['line']}. "
                            "Verify bounds checking."
                        ),
                        "line":        acc["line"],
                        "severity":    "high",
                        "source":      "rule",
                    })

        # Off-by-one in for-loop array access: i <= N instead of i < N
        off_by_one = re.findall(
            r'for\s*\([^;]*;\s*\w+\s*<=\s*(\d+)', source_code
        )
        if off_by_one:
            for ln_no, ln in enumerate(source_code.splitlines(), 1):
                if re.search(r'for\s*\([^;]*;\s*\w+\s*<=\s*\d+', ln):
                    findings.append({
                        "type":        "off_by_one_error",
                        "description": (
                            f"Loop at line {ln_no} uses '<=' which may cause "
                            "off-by-one buffer overflow."
                        ),
                        "line":        ln_no,
                        "severity":    "high",
                        "source":      "rule",
                    })

        # Nested O(n²) loops
        if parse_result.has_nested_loops:
            findings.append({
                "type":        "algorithmic_inefficiency",
                "description": (
                    "Nested loops detected (potential O(n²) complexity). "
                    "Consider algorithmic optimization."
                ),
                "line":        None,
                "severity":    "medium",
                "source":      "rule",
            })

        # Memory: malloc without free
        if len(parse_result.malloc_calls) > len(parse_result.free_calls):
            findings.append({
                "type":        "memory_leak",
                "description": (
                    f"{len(parse_result.malloc_calls)} malloc call(s) but only "
                    f"{len(parse_result.free_calls)} free call(s) found."
                ),
                "line":        parse_result.malloc_calls[0] if parse_result.malloc_calls else None,
                "severity":    "high",
                "source":      "rule",
            })

        # Division by zero heuristic — strip comments first to avoid false positives
        _src_nc = re.sub(r'//[^\n]*', '', source_code)                       # remove // comments
        _src_nc = re.sub(r'/\*.*?\*/', '', _src_nc, flags=re.DOTALL)         # remove /* */ blocks
        _CPP_KW = frozenset({
            'int', 'char', 'float', 'double', 'long', 'short', 'unsigned',
            'bool', 'void', 'return', 'if', 'else', 'for', 'while', 'do',
            'switch', 'case', 'break', 'continue', 'struct', 'class',
        })
        # Only match: something / varname  (not: varname / literal)
        div_pattern = re.findall(r'\b\w+\s*/\s*(\w+)\b', _src_nc)
        seen_div = set()
        for var in div_pattern:
            if var in seen_div or var in _CPP_KW:
                continue
            seen_div.add(var)
            # Only flag if var is assigned 0 as a direct statement
            if re.search(rf'(?:^|\s){re.escape(var)}\s*=\s*0\s*;', _src_nc, re.MULTILINE):
                findings.append({
                    "type":        "division_by_zero_risk",
                    "description": f"Variable '{var}' may be 0 when used as divisor.",
                    "line":        None,
                    "severity":    "high",
                    "source":      "rule",
                })

        logger.debug(f"Rule-based: {len(findings)} findings")
        return findings

    # ── LLM-based analysis ────────────────────────────────────────────────────

    def _llm_analysis(self, source_code, file_path, parse_result, rule_findings):
        prompt = AnalysisPromptTemplate.build(
            source_code,
            file_path,
            parse_result.to_summary(),
        )
        raw = self.llm.generate(
            prompt,
            system_prompt=AnalysisPromptTemplate.SYSTEM,
        )
        cot = self.cot_val.validate(raw)
        if cot.is_valid:
            return cot.findings, cot.reasoning_steps, cot.conclusion, cot.confidence
        else:
            logger.warning(f"LLM CoT invalid: {cot.error}")
            return [], ["Rule-based analysis only (LLM CoT invalid)."], \
                   f"{len(rule_findings)} rule-based findings.", 0.6

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _merge_findings(self, rule: List[Dict], llm: List[Dict]) -> List[Dict]:
        """Merge rule-based and LLM findings, deduplicating on (type, line) pair."""
        merged = list(rule)
        seen = {(f["type"], f.get("line")) for f in rule}
        for f in llm:
            key = (f.get("type", "unknown"), f.get("line"))
            if key not in seen:
                f.setdefault("source", "llm")
                merged.append(f)
                seen.add(key)
        return merged

    def _build_summary(self, file_path, findings, conclusion) -> str:
        high   = sum(1 for f in findings if f.get("severity") == "high")
        medium = sum(1 for f in findings if f.get("severity") == "medium")
        low    = sum(1 for f in findings if f.get("severity") == "low")
        lines  = [
            f"Analysis Report: {file_path}",
            f"Total findings : {len(findings)} "
            f"(High: {high}, Medium: {medium}, Low: {low})",
            f"Conclusion     : {conclusion}",
        ]
        for i, f in enumerate(findings, 1):
            sev  = f.get("severity", "?").upper()
            ln   = f" [line {f['line']}]" if f.get("line") else ""
            lines.append(f"  {i}. [{sev}]{ln} {f.get('type')}: {f.get('description')}")
        return "\n".join(lines)

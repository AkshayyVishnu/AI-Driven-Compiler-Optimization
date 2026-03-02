"""
Prompt Templates for AI-Driven Compiler Optimization System

Each template provides:
  - A system prompt (role description)
  - A method to build the user prompt from inputs
  - The expected CoT JSON output schema
"""

from typing import Dict, Any


# ── Shared CoT schema (documented, not enforced by these templates) ──────────
COT_SCHEMA = {
    "reasoning_steps": ["<step 1>", "<step 2>", "..."],
    "findings":        [{"type": "<str>", "description": "<str>",
                         "line": "<int|None>", "severity": "<high|medium|low>"}],
    "conclusion":      "<one-sentence summary>",
    "confidence":      "<float 0.0-1.0>",
}


class AnalysisPromptTemplate:
    """Template for the Analysis Agent."""

    SYSTEM = (
        "You are an expert C/C++ compiler analysis agent. "
        "You detect bugs, inefficiencies, and security vulnerabilities in C/C++ code. "
        "Always respond with a single JSON object that follows the CoT schema exactly. "
        "Do not include any text outside the JSON block."
    )

    @staticmethod
    def build(source_code: str, file_path: str = "", parse_summary: str = "") -> str:
        """Build the analysis user prompt."""
        parts = [
            f"Analyze the following C/C++ code for bugs, security vulnerabilities, "
            f"and performance issues.\n",
        ]
        if file_path:
            parts.append(f"File: {file_path}\n")
        if parse_summary:
            parts.append(f"Parser summary:\n{parse_summary}\n")
        parts.append(f"\nSource code:\n```cpp\n{source_code}\n```\n")
        parts.append(
            "\nRespond ONLY with a JSON object in this exact schema:\n"
            "```json\n"
            "{\n"
            '  "reasoning_steps": ["<step>", ...],\n'
            '  "findings": [\n'
            '    {"type": "<bug_type>", "description": "<detail>", '
            '"line": <line_no_or_null>, "severity": "<high|medium|low>"}\n'
            "  ],\n"
            '  "conclusion": "<summary>",\n'
            '  "confidence": <0.0-1.0>\n'
            "}\n"
            "```"
        )
        return "".join(parts)


class OptimizationPromptTemplate:
    """Template for the Optimization Agent."""

    SYSTEM = (
        "You are an expert C/C++ code optimization agent. "
        "Given source code and an analysis report, you produce corrected and optimized code. "
        "Always respond with a single JSON object that follows the CoT schema exactly."
    )

    @staticmethod
    def build(source_code: str, analysis_report: Dict[str, Any]) -> str:
        """Build the optimization user prompt."""
        findings_text = ""
        for f in analysis_report.get("all_findings", []):
            findings_text += (
                f"\n  - [{f.get('severity','?').upper()}] "
                f"{f.get('type','unknown')}: {f.get('description','')}"
                + (f" (line {f['line']})" if f.get('line') else "")
            )
        if not findings_text:
            findings_text = "\n  - No specific findings from analysis agent."

        prompt = (
            f"Optimize and fix the following C/C++ code.\n\n"
            f"Analysis findings:{findings_text}\n\n"
            f"Original code:\n```cpp\n{source_code}\n```\n\n"
            "Respond ONLY with a JSON object:\n"
            "```json\n"
            "{\n"
            '  "reasoning_steps": ["<step>", ...],\n'
            '  "findings": [\n'
            '    {"type": "<transformation>", "description": "<what changed and why>", '
            '"line": <line_no_or_null>, "severity": "info"}\n'
            "  ],\n"
            '  "optimized_code": "<full corrected C++ code as a string>",\n'
            '  "conclusion": "<summary of changes>",\n'
            '  "confidence": <0.0-1.0>\n'
            "}\n"
            "```"
        )
        return prompt


class SecurityPromptTemplate:
    """Template for the Security Agent."""

    SYSTEM = (
        "You are an expert C/C++ security analysis agent. "
        "You identify security vulnerabilities in C/C++ code with a focus on "
        "newly introduced issues versus the original. "
        "Always respond with a single JSON object that follows the CoT schema exactly. "
        "Do not include any text outside the JSON block."
    )

    @staticmethod
    def build(optimized_code: str, original_code: str = "",
              baseline_types: list = None) -> str:
        """Build the security analysis user prompt."""
        parts = ["Analyze the following C/C++ code for security vulnerabilities.\n"]
        if original_code and baseline_types:
            parts.append(
                f"NOTE: These vulnerability types were ALREADY present in the original "
                f"code before optimization: {baseline_types}. "
                "Focus on identifying NEW vulnerabilities introduced by optimization.\n\n"
            )
        parts.append(f"Code to analyze:\n```cpp\n{optimized_code}\n```\n\n")
        parts.append(
            "Respond ONLY with a JSON object in this exact schema:\n"
            "```json\n"
            "{\n"
            '  "reasoning_steps": ["<step>", ...],\n'
            '  "findings": [\n'
            '    {\n'
            '      "type": "<vulnerability_type>",\n'
            '      "description": "<detailed description>",\n'
            '      "line": <line_number_or_null>,\n'
            '      "severity": "<high|medium|low>",\n'
            '      "cwe_id": "<CWE-XXX or null>",\n'
            '      "recommendation": "<how to fix>"\n'
            '    }\n'
            "  ],\n"
            '  "overall_risk": "<critical|high|medium|low|none>",\n'
            '  "conclusion": "<summary of security posture>",\n'
            '  "confidence": <0.0-1.0>\n'
            "}\n"
            "```"
        )
        return "".join(parts)


class VerificationPromptTemplate:
    """Template for the Verification Agent's LLM reasoning pass."""

    SYSTEM = (
        "You are a formal verification reasoning agent for C/C++ code. "
        "You assess whether an optimization preserves behavioral equivalence. "
        "Always respond with a single JSON object following the CoT schema."
    )

    @staticmethod
    def build(original_code: str, optimized_code: str, diff_test_passed: bool) -> str:
        """Build the verification reasoning prompt."""
        test_status = "PASSED" if diff_test_passed else "FAILED"
        prompt = (
            f"Assess whether the optimized code is behaviorally equivalent to the original.\n\n"
            f"Differential test result: {test_status}\n\n"
            f"Original code:\n```cpp\n{original_code}\n```\n\n"
            f"Optimized code:\n```cpp\n{optimized_code}\n```\n\n"
            "Respond ONLY with a JSON object:\n"
            "```json\n"
            "{\n"
            '  "reasoning_steps": ["<step>", ...],\n'
            '  "findings": [],\n'
            '  "verdict": "<EQUIVALENT|NOT_EQUIVALENT|UNCERTAIN>",\n'
            '  "conclusion": "<explanation>",\n'
            '  "confidence": <0.0-1.0>\n'
            "}\n"
            "```"
        )
        return prompt

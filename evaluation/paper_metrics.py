"""
Pure scoring helpers for the paper experiments.

The keyword->category map is applied identically to rule, LLM and baseline
findings and is frozen (Report/experiments/category_map.json) before any run.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

# Ordered: first match wins. Patterns run on the lower-cased finding type with
# spaces/dashes normalised to underscores.
CATEGORY_RULES: List[tuple] = [
    ("performance",       r"algorithmic|loop_invariant|redundant|inefficien|scientific_numeric|memory_buffer_copy"),
    ("uninitialized",     r"uninit"),
    ("div_by_zero",       r"division|divide|modulo|div_by_zero|divide_by_zero"),
    ("double_free",       r"double_free"),
    ("use_after_free",    r"use_after_free|write_after_free"),
    ("invalid_free",      r"mismatched|invalid_free|delete_stack|free_of_stack"),
    ("leak",              r"leak"),
    ("format_string",     r"format_string|format_not_a_string"),
    ("command_injection", r"command|injection|system_call"),
    ("toctou",            r"toctou"),
    ("hardcoded_secret",  r"hardcoded|secret|credential|password"),
    ("deadlock",          r"deadlock"),
    ("data_race",         r"race"),
    ("object_slicing",    r"slicing"),
    ("type_conversion",   r"narrowing|truncat|conversion|type_mismatch|punning|aliasing|cast"),
    ("int_arith",         r"integer|signed|unsigned|shift|underflow|arith"),
    ("buffer_overflow",   r"buffer|overflow|off_by_one|strcpy|strcat|sprintf|gets|scanf|memcpy|bound|signed_index|unbounded|stack_buf|array|heap_overflow"),
    ("null_deref",        r"null|unchecked_malloc"),
    ("invalid_pointer",   r"dangling|wild|pointer|address_of_local|returning_address"),
    ("nontermination",    r"infinite|recursion|nontermination"),
    ("dead_code",         r"dead|unreachable"),
    ("missing_return",    r"missing_return|no_return|control_reaches_end"),
    ("logic_error",       r"assign|logic|condition|compar|fallthrough|fall_through|parenthes|empty_if|empty_else|switch"),
]


def _norm(text: str) -> str:
    return re.sub(r"[\s\-]+", "_", (text or "").strip().lower())


def classify_text(text: str) -> Optional[str]:
    t = _norm(text)
    for category, pattern in CATEGORY_RULES:
        if re.search(pattern, t):
            return category
    return None


def classify_finding(finding: Dict[str, Any]) -> Optional[str]:
    """Category of one finding, or None. Free-text description is consulted
    only for LLM findings (their type names are not controlled)."""
    category = classify_text(finding.get("type", ""))
    if category is None and finding.get("source") == "llm":
        category = classify_text(finding.get("description", ""))
    return category


def score_detection(findings: Iterable[Dict[str, Any]], expected: List[str]) -> Dict[str, bool]:
    found = {classify_finding(f) for f in findings}
    return {cat: cat in found for cat in expected}


def aggregate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    headline = [r for r in rows if r.get("headline")]
    multi = [r for r in rows if not r.get("headline") and len(r.get("expected", [])) > 1]

    def case_hit(r: Dict[str, Any]) -> bool:
        return bool(r["detected"]) and all(r["detected"].values())

    detected = sum(1 for r in headline if case_hit(r))
    supported = [r for r in headline if r.get("supported")]
    supported_hits = sum(1 for r in supported if case_hit(r))

    multi_total = sum(len(r["detected"]) for r in multi)
    multi_hit = sum(sum(1 for v in r["detected"].values() if v) for r in multi)

    corrected = [r for r in headline if r.get("corrected_detector") is not None]

    return {
        "headline_cases": len(headline),
        "detected_overall": detected,
        "detection_rate_overall": detected / len(headline) if headline else 0.0,
        "supported_cases": len(supported),
        "detection_rate_within_coverage": supported_hits / len(supported) if supported else 0.0,
        "multi_rule_recall": multi_hit / multi_total if multi_total else 0.0,
        "corrected_detector_judged": sum(1 for r in corrected if r["corrected_detector"]),
        "corrected_denominator": len(corrected),
        "ver_status_counts": dict(Counter(r.get("ver_status", "UNKNOWN") for r in rows)),
    }

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluation.paper_metrics import (
    aggregate,
    classify_finding,
    score_detection,
)


def test_classify_rule_types():
    assert classify_finding({"type": "uninitialized_variable"}) == "uninitialized"
    assert classify_finding({"type": "unsafe_strcpy"}) == "buffer_overflow"
    assert classify_finding({"type": "integer_overflow_malloc"}) == "int_arith"
    assert classify_finding({"type": "double_free"}) == "double_free"
    assert classify_finding({"type": "toctou_race"}) == "toctou"
    assert classify_finding({"type": "loop_invariant_strlen"}) == "performance"


def test_classify_free_form_llm_type_uses_description_only_for_llm():
    llm = {"type": "Bug", "description": "Division by zero at line 3", "source": "llm"}
    rule = {"type": "Bug", "description": "Division by zero at line 3", "source": "rule"}
    assert classify_finding(llm) == "div_by_zero"
    assert classify_finding(rule) is None


def test_score_detection_hit_and_miss():
    findings = [{"type": "unsafe_strcpy"}, {"type": "signed_index"}]
    assert score_detection(findings, ["buffer_overflow"]) == {"buffer_overflow": True}
    assert score_detection(findings, ["leak"]) == {"leak": False}


def test_aggregate_counts_and_coverage():
    rows = [
        {"tc": "TC01", "headline": True, "expected": ["uninitialized"],
         "detected": {"uninitialized": True}, "supported": True,
         "ver_status": "PASS", "corrected_detector": True},
        {"tc": "TC22", "headline": True, "expected": ["null_deref"],
         "detected": {"null_deref": False}, "supported": False,
         "ver_status": "ROLLBACK", "corrected_detector": None},
        {"tc": "TC56", "headline": False, "expected": ["leak", "dead_code"],
         "detected": {"leak": True, "dead_code": False}, "supported": True,
         "ver_status": "PASS", "corrected_detector": None},
    ]
    agg = aggregate(rows)
    assert agg["headline_cases"] == 2
    assert agg["detected_overall"] == 1
    assert agg["detection_rate_overall"] == 0.5
    assert agg["supported_cases"] == 1
    assert agg["detection_rate_within_coverage"] == 1.0
    assert agg["multi_rule_recall"] == 0.5
    assert agg["ver_status_counts"] == {"PASS": 2, "ROLLBACK": 1}

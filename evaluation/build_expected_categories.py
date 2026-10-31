"""
Freeze the experiment ground truth.

Categories are assigned from each test case's INTENDED bug (see
Report/briefs/testsuite.md), never from what the detectors currently emit.
Run once, before any experiment:  python evaluation/build_expected_categories.py
"""

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from evaluation.paper_metrics import CATEGORY_RULES, classify_text  # noqa: E402

OUT_DIR = os.path.join(ROOT, "Report", "experiments")

CATEGORY = {
    **{f"TC{n:02d}": ["uninitialized"] for n in range(1, 6)},
    **{f"TC{n:02d}": ["div_by_zero"] for n in range(6, 9)},
    **{f"TC{n:02d}": ["buffer_overflow"] for n in (9, 10, 11, 12, 13, 19, 31, 46)},
    "TC14": ["leak"], "TC20": ["leak"], "TC40": ["leak"],
    **{f"TC{n}": ["leak"] for n in (41, 42, 43)},
    "TC15": ["double_free"],
    "TC16": ["use_after_free"], "TC21": ["use_after_free"], "TC25": ["use_after_free"],
    "TC17": ["invalid_free"], "TC18": ["invalid_free"],
    "TC22": ["null_deref"], "TC26": ["null_deref"],
    "TC23": ["invalid_pointer"], "TC24": ["invalid_pointer"],
    **{f"TC{n}": ["int_arith"] for n in (27, 28, 29, 30, 50)},
    **{f"TC{n}": ["logic_error"] for n in (32, 33, 38, 39)},
    "TC34": ["nontermination"], "TC37": ["nontermination"],
    "TC35": ["dead_code"], "TC36": ["missing_return"],
    **{f"TC{n}": ["type_conversion"] for n in (44, 45, 47)},
    "TC48": ["format_string"], "TC49": ["command_injection"],
    "TC51": ["toctou"], "TC52": ["hardcoded_secret"],
    "TC53": ["data_race"], "TC54": ["deadlock"], "TC55": ["object_slicing"],
    "TC56": ["uninitialized", "buffer_overflow", "leak", "div_by_zero",
             "type_conversion", "dead_code", "logic_error", "performance"],
    "TC57": ["uninitialized", "buffer_overflow"],
    "TestCase1": ["uninitialized", "div_by_zero"],
}

# Every finding `type` the detectors in src/ can emit (grep of analysis_agent,
# security_scanner, security_agent, domain_rules). Used to compute which
# categories are reachable at all ("detector coverage").
DETECTOR_VOCAB = """
uninitialized_variable potential_buffer_overflow off_by_one_error algorithmic_inefficiency
memory_leak division_by_zero_risk type_mismatch_int_string loop_invariant_strlen
redundant_constant_in_loop loop_invariant_sizeof empty_if_body empty_else_body dead_code_after_return
unsafe_gets unsafe_scanf_s unsafe_strcpy unsafe_strcat unsafe_sprintf format_string_bug use_after_free
double_free unchecked_malloc hardcoded_secret command_injection toctou_race integer_overflow_malloc
unsafe_memcpy insecure_rand atoi_no_validate signed_index stack_buf_overflow taint_flow_risk
signed_unsigned_mismatch unbounded_loop_write stack_overflow_risk race_condition_risk
scientific_numeric_reduction memory_buffer_copy_loop
""".split()

# Cases excluded from the headline set: TC40's ifstream is closed by RAII (not a
# real bug); multi-rule cases are scored by recall instead.
NOT_HEADLINE = {"TC40", "TC56", "TC57", "TestCase1"}


def parse_table(md_path):
    flags = {}
    for line in open(md_path, encoding="utf-8"):
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 10 or not re.match(r"(TC\d+|TestCase1)$", cols[0]):
            continue
        flags[cols[0]] = {
            "intended_bug": cols[3],
            "sol_file": None if cols[5] == "none" else cols[5],
            "reads_stdin": cols[6].startswith("yes"),
            "compiles_here": cols[7].startswith("pass"),
            "nondeterministic": cols[8].startswith("yes"),
        }
    return flags


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    flags = parse_table(os.path.join(ROOT, "Report", "briefs", "testsuite.md"))
    reachable = {classify_text(t) for t in DETECTOR_VOCAB} - {None}

    cases = {}
    for tc, cats in CATEGORY.items():
        f = flags.get(tc, {})
        cases[tc] = {
            "expected": cats,
            "headline": tc not in NOT_HEADLINE,
            "supported": all(c in reachable for c in cats),
            **f,
        }
    # TestCase1's fixed version has no extension and a non-numeric name.
    cases["TestCase1"]["sol_file"] = "testCase1"

    with open(os.path.join(OUT_DIR, "expected_categories.json"), "w", encoding="utf-8") as fh:
        json.dump(cases, fh, indent=2)
    with open(os.path.join(OUT_DIR, "category_map.json"), "w", encoding="utf-8") as fh:
        json.dump({"rules": [[c, p] for c, p in CATEGORY_RULES],
                   "detector_vocabulary": DETECTOR_VOCAB,
                   "reachable_categories": sorted(reachable)}, fh, indent=2)
    unsupported = sorted(tc for tc, c in cases.items() if c["headline"] and not c["supported"])
    print(f"{len(cases)} cases; {sum(c['headline'] for c in cases.values())} headline; "
          f"{len(unsupported)} headline cases without any reachable detector")
    print("reachable:", sorted(reachable))
    print("unsupported:", unsupported)


if __name__ == "__main__":
    main()

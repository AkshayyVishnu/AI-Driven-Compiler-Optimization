# Complete Test Report

**Generated:** 2026-04-19T12:26:06.358429Z  
**Evaluation mode:** deterministic rule-based (`--no-llm`)  

## Summary

- Cases executed: **12**
- Workflow PASS: **10**
- Workflow ROLLBACK: **0**
- Workflow ESCALATE: **2**
- New vulnerabilities introduced: **0**
- Correctness-style pass rate: **83.3%**

## Per-Case Results

| File | Bucket | Workflow | Iterations | Verification | Security | New Vulns | Risk |
|------|--------|----------|------------|--------------|----------|-----------|------|
| `TC01_uninit_arithmetic.cpp` | correctness | PASS | 0 | PASS | PASS | 0 | none |
| `TC07_div_by_zero_var.cpp` | correctness | PASS | 0 | PASS | PASS | 0 | none |
| `TC11_buffer_overflow_loop.cpp` | security | PASS | 0 | PASS | PASS | 0 | none |
| `TC12_strcpy_overflow.cpp` | security | PASS | 0 | PASS | PASS | 0 | medium |
| `TC14_memory_leak.cpp` | correctness | PASS | 0 | PASS | PASS | 0 | none |
| `TC16_use_after_free.cpp` | rollback | ESCALATE | 1 | ROLLBACK | PASS | 0 | high |
| `TC20_leak_in_loop.cpp` | correctness | PASS | 0 | PASS | PASS | 0 | none |
| `TC27_int_overflow.cpp` | security | PASS | 0 | PASS | PASS | 0 | none |
| `TC31_off_by_one.cpp` | correctness | ESCALATE | 1 | ROLLBACK | PASS | 0 | none |
| `TC35_unreachable_code.cpp` | correctness | PASS | 0 | PASS | PASS | 0 | none |
| `TC39_empty_if_body.cpp` | correctness | PASS | 0 | PASS | PASS | 0 | none |
| `TC41_leak_early_return.cpp` | correctness | PASS | 0 | PASS | PASS | 0 | none |

## Acceptance Check

- Clean/safe outcomes are represented by the **10** PASS cases.
- Rollback behavior is represented by the **0** rollback cases.
- Security regression count from measured runs is **0**.
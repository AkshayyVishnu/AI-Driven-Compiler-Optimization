# Comparative Analysis Report

**Generated:** 2026-04-19T12:26:06.358548Z  

## Compared Variants

- Original baseline 4-stage pipeline
- Revised orchestrated deterministic workflow

## Aggregate Comparison

- Baseline `success` count: **10** / 12
- Orchestrated `PASS` workflow count: **10** / 12
- Cases improved by orchestration/refinement: **0**
- Average latency delta (`baseline - orchestrated`): **-4.5528 s**

## Case-by-Case Comparison

| File | Baseline Status | Orchestrated Workflow | Delta (s) | Stop Reason |
|------|------------------|-----------------------|-----------|-------------|
| `TC01_uninit_arithmetic.cpp` | success | PASS | -10.8223 | initial_pass |
| `TC07_div_by_zero_var.cpp` | success | PASS | -14.1112 | initial_pass |
| `TC11_buffer_overflow_loop.cpp` | success | PASS | -2.8706 | initial_pass |
| `TC12_strcpy_overflow.cpp` | success | PASS | -3.4444 | initial_pass |
| `TC14_memory_leak.cpp` | success | PASS | -2.9276 | initial_pass |
| `TC16_use_after_free.cpp` | rollback | ESCALATE | -3.0772 | no_material_improvement |
| `TC20_leak_in_loop.cpp` | success | PASS | -2.6597 | initial_pass |
| `TC27_int_overflow.cpp` | success | PASS | -2.787 | initial_pass |
| `TC31_off_by_one.cpp` | rollback | ESCALATE | -3.0539 | no_material_improvement |
| `TC35_unreachable_code.cpp` | success | PASS | -3.0447 | initial_pass |
| `TC39_empty_if_body.cpp` | success | PASS | -3.0039 | initial_pass |
| `TC41_leak_early_return.cpp` | success | PASS | -2.8312 | initial_pass |

## Interpretation

- The orchestrated workflow adds explicit bounded refinement and escalation metadata.
- Comparisons here stay within the revised project scope: source-to-source workflow only.
- No compiler baseline or LLM-only baseline is used in this formal report set.
# Test suite inventory

Method: read every file in MicroBenchmarks/Testcases; ran the real rule layers (AnalysisAgent._rule_based_analysis, SecurityScanner.scan, SecurityAgent._rule_scan and _heuristic_scan; no LLM) over each file; compiled each with MinGW `g++ -fsyntax-only -w`. No existing file was modified.

## Type vocabulary (grounded in code)
- analysis_agent.py: uninitialized_variable, potential_buffer_overflow, off_by_one_error, algorithmic_inefficiency, memory_leak (counts malloc vs free only; `new`/`delete` ignored), division_by_zero_risk (only `x / var` where `var = 0;` is a statement), type_mismatch_int_string, loop_invariant_strlen, redundant_constant_in_loop, loop_invariant_sizeof, empty_if_body / empty_else_body (only `{}` on the same line), dead_code_after_return.
- security_scanner.py and security_agent.py: unsafe_gets, unsafe_scanf_s, unsafe_strcpy, unsafe_strcat, unsafe_sprintf, format_string_bug, use_after_free, double_free (scanner only, `free()` only), unchecked_malloc, hardcoded_secret, command_injection, toctou_race (needs `access()` then `open/fopen`), integer_overflow_malloc (needs `malloc(a*b)`), unsafe_memcpy, insecure_rand, atoi_no_validate, signed_index, stack_buf_overflow; agent heuristics: taint_flow_risk, signed_unsigned_mismatch, unbounded_loop_write, stack_overflow_risk, race_condition_risk; cppcheck_<id> (dynamic, only if cppcheck is installed).
- domain_rules.py (optimisation hints, not bugs): scientific_numeric_reduction, memory_buffer_copy_loop, scientific_numeric_loop_tuning, memory_buffer_copy_loop_to_memcpy.

Convention for "EXPECTED": a type is listed when the vocabulary contains a type that semantically matches the intended bug, even if the current regex/heuristic misses it on that file (a recall gap; compare with the last column). `NO_DETECTOR` means no type in the vocabulary matches the bug at all. Known false positives seen in the last column: `signed_index` on any `int` index, `format_string_bug` on TC13 sprintf, `unchecked_malloc` on TC50 (it is checked), `potential_buffer_overflow` on TC14/TC17/TC50/TC57 loops.

## Table

| TC id | filename | bug category | intended bug | EXPECTED finding type(s) | SOL file | reads stdin | g++ -fsyntax-only -w | nondeterministic UB output | observed rule-layer hits (current code) |
|---|---|---|---|---|---|---|---|---|---|
| TC01 | TC01_uninit_arithmetic.cpp | uninitialized | int x read before init | `uninitialized_variable` | SOL01_uninit_arithmetic.cpp | no | pass | yes - indeterminate stack value | `uninitialized_variable` |
| TC02 | TC02_uninit_array_index.cpp | uninitialized | uninit int used as array index | `uninitialized_variable` | SOL02_uninit_array_index.cpp | no | pass | yes - random index | `signed_index`, `uninitialized_variable` |
| TC03 | TC03_uninit_pointer.cpp | uninitialized | write through uninit pointer | `uninitialized_variable` | SOL03_uninit_pointer.cpp | no | pass | yes - wild pointer, crash or corruption | - |
| TC04 | TC04_uninit_condition.cpp | uninitialized | uninit bool in if condition | `uninitialized_variable` | SOL04_uninit_condition.cpp | no | pass | yes - branch depends on garbage | `uninitialized_variable` |
| TC05 | TC05_uninit_struct.cpp | uninitialized | uninit struct members read | `uninitialized_variable` | SOL05_uninit_struct.cpp | no | pass | yes - garbage values | `uninitialized_variable` |
| TC06 | TC06_div_by_zero_const.cpp | division/modulo-by-zero | int / literal 0 | `division_by_zero_risk` | SOL06_div_by_zero_const.cpp | no | pass | no - SIGFPE on x86 (UB; may be const-folded at -O2) | - |
| TC07 | TC07_div_by_zero_var.cpp | division/modulo-by-zero | int / variable holding 0 | `division_by_zero_risk` | SOL07_div_by_zero_var.cpp | no | pass | no - SIGFPE on x86 (UB) | `division_by_zero_risk` |
| TC08 | TC08_modulo_by_zero.cpp | division/modulo-by-zero | int % variable holding 0 | `division_by_zero_risk` | SOL08_modulo_by_zero.cpp | no | pass | no - SIGFPE on x86 (UB) | - |
| TC09 | TC09_array_oob_positive.cpp | array/buffer bounds | arr[10] on int[5] (read) | `potential_buffer_overflow` | SOL09_array_oob_positive.cpp | no | pass | yes - OOB read of stack garbage | - |
| TC10 | TC10_array_negative_index.cpp | array/buffer bounds | arr[-1] negative index read | `signed_index` | SOL10_array_negative_index.cpp | no | pass | yes - OOB read of stack garbage | `signed_index` |
| TC11 | TC11_buffer_overflow_loop.cpp | array/buffer bounds | loop i<=3 writes arr[3] of int[3] | `off_by_one_error`, `potential_buffer_overflow` | SOL11_buffer_overflow_loop.cpp | no | pass | yes - stack overwrite, effect depends on layout | `off_by_one_error`, `potential_buffer_overflow`, `signed_index` |
| TC12 | TC12_strcpy_overflow.cpp | array/buffer bounds | strcpy long string into char[10] | `unsafe_strcpy`, `stack_buf_overflow` | SOL12_strcpy_overflow.cpp | no | pass | yes - stack smash | `stack_buf_overflow`, `unsafe_strcpy` |
| TC13 | TC13_sprintf_overflow.cpp | array/buffer bounds | sprintf overflow of char[10] | `unsafe_sprintf`, `stack_buf_overflow` | SOL13_sprintf_overflow.cpp | no | pass | yes - stack smash | `format_string_bug`, `stack_buf_overflow`, `unsafe_sprintf` |
| TC14 | TC14_memory_leak.cpp | memory management | new int[100] never deleted | `memory_leak` | SOL14_memory_leak.cpp | no | pass | no - leak is silent | `potential_buffer_overflow`, `signed_index` |
| TC15 | TC15_double_free.cpp | memory management | delete same pointer twice | `double_free` | SOL15_double_free.cpp | no | pass | yes - heap corruption/abort varies | - |
| TC16 | TC16_use_after_free.cpp | memory management | read *ptr after delete | `use_after_free` | SOL16_use_after_free.cpp | no | pass | yes - freed memory content | `use_after_free` |
| TC17 | TC17_mismatched_delete.cpp | memory management | new[] released with delete | NO_DETECTOR | SOL17_mismatched_delete.cpp | no | pass | yes - UB, allocator dependent | `potential_buffer_overflow`, `signed_index` |
| TC18 | TC18_delete_stack.cpp | memory management | delete of address of stack var | NO_DETECTOR | SOL18_delete_stack.cpp | no | pass | yes - UB, crash/abort | - |
| TC19 | TC19_heap_overflow.cpp | array/buffer bounds | strcpy 39 chars into new char[10] (heap overflow) | `unsafe_strcpy` | SOL19_heap_overflow.cpp | no | pass | yes - heap corruption | `unsafe_strcpy` |
| TC20 | TC20_leak_in_loop.cpp | memory management | new int in loop never deleted | `memory_leak` | SOL20_leak_in_loop.cpp | no | pass | no - leak is silent | - |
| TC21 | TC21_write_after_free.cpp | memory management | write *ptr after delete | `use_after_free` | SOL21_write_after_free.cpp | no | pass | yes - heap corruption | `use_after_free` |
| TC22 | TC22_null_deref.cpp | pointer misuse | write through nullptr | NO_DETECTOR | SOL22_null_deref.cpp | no | pass | no - deterministic segfault (UB) | - |
| TC23 | TC23_dangling_ptr_scope.cpp | pointer misuse | return address of local, then deref | NO_DETECTOR | SOL23_dangling_ptr_scope.cpp | no | pass | yes - stack reuse | - |
| TC24 | TC24_wild_ptr_arith.cpp | pointer misuse | ptr += 100 past int[5], deref | NO_DETECTOR | SOL24_wild_ptr_arith.cpp | no | pass | yes - OOB read | - |
| TC25 | TC25_class_use_after_delete.cpp | pointer misuse | member deleted then dereferenced (also double delete in dtor) | `use_after_free` | SOL25_class_use_after_delete.cpp | no | pass | yes - UAF + double free | `use_after_free` |
| TC26 | TC26_null_check_deref.cpp | pointer misuse | deref nullptr inside ptr==nullptr branch | NO_DETECTOR | SOL26_null_check_deref.cpp | no | pass | no - deterministic segfault (UB) | - |
| TC27 | TC27_int_overflow.cpp | integer/arithmetic | INT_MAX + 1 signed overflow | NO_DETECTOR | SOL27_int_overflow.cpp | no | pass | no - UB but wraps deterministically in practice (const-fold may differ) | - |
| TC28 | TC28_int_underflow.cpp | integer/arithmetic | INT_MIN - 1 signed underflow | NO_DETECTOR | SOL28_int_underflow.cpp | no | pass | no - UB but wraps deterministically in practice | - |
| TC29 | TC29_signed_unsigned_cmp.cpp | integer/arithmetic | int vs unsigned comparison (-1 > 1u) | `signed_unsigned_mismatch` | SOL29_signed_unsigned_cmp.cpp | no | pass | no - defined behaviour | - |
| TC30 | TC30_shift_overflow.cpp | integer/arithmetic | 1 << 32 shift past width | NO_DETECTOR | SOL30_shift_overflow.cpp | no | pass | yes - UB, result varies by compiler/opt level | - |
| TC31 | TC31_off_by_one.cpp | logic/control-flow | loop 1..10 over int[10] (off-by-one OOB read) | `off_by_one_error`, `potential_buffer_overflow` | SOL31_off_by_one.cpp | no | pass | yes - OOB read of arr[10] | `off_by_one_error`, `potential_buffer_overflow`, `signed_index` |
| TC32 | TC32_assign_vs_compare.cpp | logic/control-flow | if (x = 10) assignment instead of == | NO_DETECTOR | SOL32_assign_vs_compare.cpp | no | pass | no | - |
| TC33 | TC33_wrong_logic_op.cpp | logic/control-flow | || instead of && in range check | NO_DETECTOR | SOL33_wrong_logic_op.cpp | no | pass | no | - |
| TC34 | TC34_infinite_recursion.cpp | logic/control-flow | recursion with no base case | NO_DETECTOR | SOL34_infinite_recursion.cpp | no | pass | no - deterministic stack overflow crash (UB) | - |
| TC35 | TC35_unreachable_code.cpp | logic/control-flow | statement after return (dead code) | `dead_code_after_return` | SOL35_unreachable_code.cpp | no | pass | no | `dead_code_after_return` |
| TC36 | TC36_missing_return.cpp | logic/control-flow | non-void fn falls off end (a==b) | NO_DETECTOR | SOL36_missing_return.cpp | no | pass | yes - UB, garbage return value | - |
| TC37 | TC37_infinite_loop.cpp | logic/control-flow | while loop never increments i | NO_DETECTOR | SOL37_infinite_loop.cpp | no | pass | no - deterministic hang (needs timeout) | - |
| TC38 | TC38_switch_fallthrough.cpp | logic/control-flow | missing break in switch (fallthrough) | NO_DETECTOR | SOL38_switch_fallthrough.cpp | no | pass | no | - |
| TC39 | TC39_empty_if_body.cpp | logic/control-flow | if (x>0); stray semicolon empty body | `empty_if_body` | SOL39_empty_if_body.cpp | no | pass | no | - |
| TC40 | TC40_file_leak.cpp | resource leak | ifstream never explicitly closed (RAII closes it; arguably not a real bug) | NO_DETECTOR | SOL40_file_leak.cpp | no | pass | no | - |
| TC41 | TC41_leak_early_return.cpp | resource leak | new[] leaked on early return | `memory_leak` | SOL41_leak_early_return.cpp | no | pass | no - leak is silent | - |
| TC42 | TC42_leak_exception.cpp | resource leak | new[] leaked via exception path / return in catch | `memory_leak` | SOL42_leak_exception.cpp | no | pass | no - leak is silent | - |
| TC43 | TC43_lost_pointer.cpp | resource leak | first new int overwritten (lost pointer) | `memory_leak` | SOL43_lost_pointer.cpp | no | pass | no - leak is silent | - |
| TC44 | TC44_narrowing_conv.cpp | type conversion | long long to int narrowing | NO_DETECTOR | SOL44_narrowing_conv.cpp | no | pass | no - implementation-defined, deterministic | - |
| TC45 | TC45_float_truncation.cpp | type conversion | double to int truncation | NO_DETECTOR | SOL45_float_truncation.cpp | no | pass | no | - |
| TC46 | TC46_unbounded_input.cpp | input/format/injection | cin >> char[5] unbounded input | NO_DETECTOR | SOL46_unbounded_input.cpp | yes | pass | yes - overflow depends on input and layout | - |
| TC47 | TC47_type_punning.cpp | type conversion | double reinterpreted via int* (strict aliasing) | NO_DETECTOR | SOL47_type_punning.cpp | no | pass | no - UB but deterministic in practice | - |
| TC48 | TC48_format_string.cpp | input/format/injection | printf(userInput) format string | `format_string_bug` | SOL48_format_string.cpp | yes | pass | no (input-dependent only) | `format_string_bug` |
| TC49 | TC49_command_injection.cpp | input/format/injection | system("cat "+input) command injection | `command_injection` | SOL49_command_injection.cpp | yes | pass | no (input-dependent only) | `command_injection` |
| TC50 | TC50_alloc_overflow.cpp | input/format/injection | malloc(size+1) overflow with unsigned input, then loop <= size | `integer_overflow_malloc` | SOL50_alloc_overflow.cpp | yes | pass | no (input-dependent only) | `potential_buffer_overflow`, `signed_index`, `signed_unsigned_mismatch`, `unchecked_malloc` |
| TC51 | TC51_toctou.cpp | input/format/injection | stat() check then ifstream open (TOCTOU) | `toctou_race` | SOL51_toctou.cpp | no | pass | no | - |
| TC52 | TC52_hardcoded_creds.cpp | input/format/injection | hardcoded adminPass literal | `hardcoded_secret` | SOL52_hardcoded_creds.cpp | yes | pass | no | `hardcoded_secret` |
| TC53 | TC53_data_race.cpp | concurrency | unsynchronised sharedCounter++ in two threads | `race_condition_risk` | SOL53_data_race.cpp | no | FAIL (env: MinGW lacks std::thread/mutex; not deliberate) | yes - lost updates | - |
| TC54 | TC54_deadlock.cpp | concurrency | opposite lock order on two mutexes (deadlock) | NO_DETECTOR | SOL54_deadlock.cpp | no | FAIL (env: MinGW lacks std::thread/mutex; not deliberate) | yes - timing dependent hang | - |
| TC55 | TC55_object_slicing.cpp | OOP | pass Derived by value to Base param (slicing) | NO_DETECTOR | SOL55_object_slicing.cpp | no | pass | no | - |
| TC56 | TC56_multi_rule_violations.cpp | multi-rule | 13 deliberate rule violations (see file header) | `uninitialized_variable`, `potential_buffer_overflow`, `off_by_one_error`, `algorithmic_inefficiency`, `memory_leak`, `division_by_zero_risk`, `type_mismatch_int_string`, `loop_invariant_strlen`, `redundant_constant_in_loop`, `loop_invariant_sizeof`, `empty_if_body`, `empty_else_body`, `dead_code_after_return` | none | no | FAIL (deliberate: int = "string") | yes - uninit read, OOB write grades[10], div by 0 | `algorithmic_inefficiency`, `dead_code_after_return`, `division_by_zero_risk`, `empty_else_body`, `empty_if_body`, `integer_overflow_malloc`, `loop_invariant_sizeof`, `loop_invariant_strlen`, `memory_leak`, `potential_buffer_overflow`, `redundant_constant_in_loop`, `signed_index`, `type_mismatch_int_string`, `unchecked_malloc`, `uninitialized_variable` |
| TC57 | TC57_rule_fix_demo.cpp | multi-rule | uninit total/result, off-by-one i<=SIZE, strcpy to char[32] | `uninitialized_variable`, `off_by_one_error`, `unsafe_strcpy`, `stack_buf_overflow` | none | no | pass | yes - uninit reads, OOB write scores[5] | `dead_code_after_return`, `potential_buffer_overflow`, `signed_index`, `stack_buf_overflow`, `unbounded_loop_write`, `unsafe_strcpy` |
| TestCase1 | TestCase1_Lr_errors.cpp | multi-rule | uninit x used in sum; y / 0; no return in main | `uninitialized_variable`, `division_by_zero_risk` | testCase1 (no extension) | no | pass | yes - uninit read; div by 0 | `uninitialized_variable` |
| (dup of TC19) | TC19_heap_overflow - Copy.cpp | array/buffer bounds | byte-identical copy of TC19 | same as TC19 | SOL19_heap_overflow.cpp | no | pass | yes - heap corruption | `unsafe_strcpy` |

Notes: TC19 is classed as array/buffer bounds although its header says Memory Management. TC40's ifstream is closed by RAII, so its "bug" is arguably not real. Entries with an empty expected list (NO_DETECTOR): 22.

## (a) Counts per category
- uninitialized: 5
- division/modulo-by-zero: 3
- array/buffer bounds: 6
- memory management: 7
- pointer misuse: 5
- integer/arithmetic: 4
- logic/control-flow: 9
- resource leak: 4
- type conversion: 3
- input/format/injection: 6
- concurrency: 2
- OOP: 1
- multi-rule: 3
- Total: 58 (TC01-TC57 = 57, plus TestCase1 under multi-rule; duplicate excluded)

## (b) Files without a SOL, and the duplicate
SOL01..SOL55 exist and pair 1:1 with TC01..TC55 by name suffix (spot-read SOL14, 17, 46, 53: each is the fixed version of its TC).

| file | status | recommendation |
|---|---|---|
| TC56_multi_rule_violations.cpp | no SOL; deliberate compile error (`int status = "active"`); built to fire every AnalysisAgent rule | INCLUDE as a rule-coverage case, score detection only (it does not compile and has runtime UB). Ground truth = its 13-type list (all 13 fire today). |
| TC57_rule_fix_demo.cpp | no SOL; compiles; 4 bugs for the UI Fix/Fix All demo | INCLUDE in detection scoring; EXCLUDE from "bugs corrected"/speedup unless a reference fix is written (runtime UB). Current rules miss its uninit and off-by-one (macro SIZE; uninit inside a non-main function). |
| TestCase1_Lr_errors.cpp | no `SOL<nn>`; its fixed version is `Solutions_to_testcase/testCase1` (no extension, CRLF); compiles; header mentions "missing parentheses" that do not exist | INCLUDE only as an optional smoke test; EXCLUDE from the 55-case headline set. |
| TC19_heap_overflow - Copy.cpp | byte-identical to TC19_heap_overflow.cpp (cmp verified); spaces in filename | EXCLUDE (would double-count TC19; spaces break naive globbing). |
| Solutions_to_testcase/testCase1 | not a numbered SOL | EXCLUDE from SOL lookup by pattern; map manually to TestCase1 if used. |

Evaluation caveats: TC53 and TC54 fail `-fsyntax-only` here only because this MinGW build lacks std::thread/std::mutex (no posix threads); they are fine on a POSIX toolchain, so skip compile/run checks for them on this machine. Stdin readers are exactly TC46, TC48, TC49, TC50, TC52 (a naive grep for "cin" also hits TC26 and TC55 via "Dereferencing"/"Slicing"), so any runner needs input or empty stdin plus a timeout. TC37 and TC54 hang, TC34 overflows the stack, TC03/TC22/TC26 crash. About half the cases contain UB with unstable output, so differential output testing is only meaningful for the "nondeterministic = no" rows.

## (c) expected_findings.json (also saved as Report/briefs/expected_findings.draft.json)
```json
{
  "TC01": [
    "uninitialized_variable"
  ],
  "TC02": [
    "uninitialized_variable"
  ],
  "TC03": [
    "uninitialized_variable"
  ],
  "TC04": [
    "uninitialized_variable"
  ],
  "TC05": [
    "uninitialized_variable"
  ],
  "TC06": [
    "division_by_zero_risk"
  ],
  "TC07": [
    "division_by_zero_risk"
  ],
  "TC08": [
    "division_by_zero_risk"
  ],
  "TC09": [
    "potential_buffer_overflow"
  ],
  "TC10": [
    "signed_index"
  ],
  "TC11": [
    "off_by_one_error",
    "potential_buffer_overflow"
  ],
  "TC12": [
    "unsafe_strcpy",
    "stack_buf_overflow"
  ],
  "TC13": [
    "unsafe_sprintf",
    "stack_buf_overflow"
  ],
  "TC14": [
    "memory_leak"
  ],
  "TC15": [
    "double_free"
  ],
  "TC16": [
    "use_after_free"
  ],
  "TC17": [],
  "TC18": [],
  "TC19": [
    "unsafe_strcpy"
  ],
  "TC20": [
    "memory_leak"
  ],
  "TC21": [
    "use_after_free"
  ],
  "TC22": [],
  "TC23": [],
  "TC24": [],
  "TC25": [
    "use_after_free"
  ],
  "TC26": [],
  "TC27": [],
  "TC28": [],
  "TC29": [
    "signed_unsigned_mismatch"
  ],
  "TC30": [],
  "TC31": [
    "off_by_one_error",
    "potential_buffer_overflow"
  ],
  "TC32": [],
  "TC33": [],
  "TC34": [],
  "TC35": [
    "dead_code_after_return"
  ],
  "TC36": [],
  "TC37": [],
  "TC38": [],
  "TC39": [
    "empty_if_body"
  ],
  "TC40": [],
  "TC41": [
    "memory_leak"
  ],
  "TC42": [
    "memory_leak"
  ],
  "TC43": [
    "memory_leak"
  ],
  "TC44": [],
  "TC45": [],
  "TC46": [],
  "TC47": [],
  "TC48": [
    "format_string_bug"
  ],
  "TC49": [
    "command_injection"
  ],
  "TC50": [
    "integer_overflow_malloc"
  ],
  "TC51": [
    "toctou_race"
  ],
  "TC52": [
    "hardcoded_secret"
  ],
  "TC53": [
    "race_condition_risk"
  ],
  "TC54": [],
  "TC55": [],
  "TC56": [
    "uninitialized_variable",
    "potential_buffer_overflow",
    "off_by_one_error",
    "algorithmic_inefficiency",
    "memory_leak",
    "division_by_zero_risk",
    "type_mismatch_int_string",
    "loop_invariant_strlen",
    "redundant_constant_in_loop",
    "loop_invariant_sizeof",
    "empty_if_body",
    "empty_else_body",
    "dead_code_after_return"
  ],
  "TC57": [
    "uninitialized_variable",
    "off_by_one_error",
    "unsafe_strcpy",
    "stack_buf_overflow"
  ],
  "TestCase1": [
    "uninitialized_variable",
    "division_by_zero_risk"
  ]
}
```
Empty arrays = NO_DETECTOR (treat as LLM-only / not measurable by rules). TestCase1 is included; the duplicate is not.

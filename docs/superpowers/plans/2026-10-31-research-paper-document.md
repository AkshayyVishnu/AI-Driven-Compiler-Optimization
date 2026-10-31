# DeepCompile Research-Paper Document Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Sonnet subagents do all context gathering, coding and drafting; the Opus `advisor` tool is consulted only for guidance and review and writes nothing. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Produce one Markdown paper, `Report/DeepCompile_Paper.md`, for a local-conference submission: what DeepCompile does, architecture, methodology, experiment results, advantages/limitations, threats to validity.

**Architecture:** Phase 1 Sonnet agents write briefs for the files not yet read. Phase 3 builds a small experiment harness (TDD) that runs the real pipeline and writes raw JSON + CSV. Phase 4 drafts the paper with every table generated from those CSVs. Phase 5 audits each claim and sends the draft to the advisor.

**Tech Stack:** Python 3.13, pytest, g++ (MinGW 6.3.0), Ollama (qwen2.5-coder:7b) and optionally Gemini, Markdown + mermaid.

**Spec (inline):** Outline = Abstract, Introduction, Related Work, Architecture, Methodology, Experimental Setup, Results, Advantages, Limitations, Threats to Validity, Conclusion. Acceptance: every number traces to a file under `Report/experiments/`; every architecture claim cites `file:line`; no Z3 / formal-verification claims; multi-agent described as "shared context + observed message trace" (agents call each other directly; `Pipeline._route` only logs).

## Global Constraints

- No numbers are copied from the old PDFs, `FINAL_20_PAGE_REPORT.md` or `Report/` drafts (produced while the perf harness was broken).
- Z3 is out of scope (user preference); report it as present-but-skipped.
- **Framing rule (user, mid-session):** in the Architecture, Methodology and every other paper file, describe the components that WORK TODAY as the core system and results. Components that need fixes are included as clearly marked **optional modules / future extensions**, not as validated contributions. Initial classification (verify against experiment results before writing):
  - Core (working): rule-based analysis, rule-based optimizer transforms that pass verification, differential testing (g++ compile + stdout compare), security scanner/agent layers 1-2, shared ContextManager, orchestrator workflow, Flask/React UI, SSE streaming, explainability reports.
  - Optional / future extension (need fixes): LLM-guided refinement (client stays disabled after cycle 1), LLM layers (truncation at 2048 tokens, cache ignores backend), performance benchmarking and speedup % (harness fix pending/just applied), Z3 equivalence (not installed), real inter-agent message passing (framework exists but pipeline only logs), unsafe transforms (strength reduction, blanket off-by-one), per-transform rollback, hardware energy monitoring, cppcheck layer (not installed).
  - Each optional item gets: what it is, why it is not yet in the core results, the concrete fix (file:line), and what it would enable.
- Metrics: bugs identified, bugs corrected, speedup %.
- **LLM scope (user decision):** evaluate rule-only and Gemini configs. Ollama is NOT run; the paper states it is a supported backend implemented through the same `LLMClient` interface (`src/llm/llm_client.py`) but not evaluated in this study. Do not report any Ollama numbers.
- Each configuration runs in its own subprocess, and the four module caches (`_ANALYSIS_CACHE`, `_OPTIMIZATION_CACHE`, `_VERIFICATION_CACHE`, `_SECURITY_CACHE`) are `.clear()`ed before every case and timing repeat. (`use_cache` cannot be passed through `pipeline.run()` / the orchestrator.)
- Optimizer output goes to `Report/experiments/opt_out/` by patching `OptimizationAgent.__init__.__defaults__` to `(None, <exp_dir>)` (pipeline, orchestrator and RefinementAgent each build their own agent; the default is bound at class definition). A test asserts a run writes nothing into `MicroBenchmarks/Generated_optimisation` (it has staged user changes).
- Every case runs under a hard subprocess timeout (TC37 and TC54 hang).
- Scoring: match at CATEGORY level through one keyword->category map frozen in `expected_findings.json` before the first run; expected categories come from each TC's intended bug, not from what detectors currently emit (spot-check >=5 rows incl. TC56). NO_DETECTOR cases count as misses; report "overall" and "within detector coverage" separately.
- "Corrected" is reported as `detector-judged` (circular: same regexes) plus `output matches SOL` for deterministic cases, plus an independent oracle (clang --analyze / clang-tidy) if available.
- Baseline: `g++ -Wall -Wextra` (and clang-tidy / `clang --analyze` if present) on all TCs through the same category map.
- Perf is measured separately, sequentially, after the pipeline, on original vs final code, only for verification-PASS cases whose code changed; report absolute ms and flag <1 ms as noise. Any curated speedup kernel set is a user decision and labelled as such.
- Citations: only references verified by a Sonnet agent with WebSearch against a real DOI/arXiv/publisher URL, recorded beside each; drop the rest (8-12 solid refs suffice).
- Paper describes `src/` only (top-level `agents/` and `utils/` are a legacy copy). Run pytest only on the new test files (3 pre-existing failures).
- No commits unless the user asks (branch is `main`).

## Review Focus

- Programs whose original fails to compile (several TCs): diff-test is not "PASS"; count as `original_compile_error`, not as a verified correction.
- TCs with undefined behaviour (uninit, UAF): output differs between runs; mark outputs `nondeterministic`, do not call them regressions.
- Programs that read stdin: the testers feed empty stdin; harness must record that.
- TC56, TC57, `TestCase1_Lr_errors.cpp` and `TC19_... - Copy.cpp` have no SOL file or are duplicates; they must be excluded or flagged, not silently counted.
- A config where the LLM was unreachable must be labelled `llm_fallback` per TC (stub or invalid-JSON fallback), otherwise "LLM" rows are really rule-only rows.

---

## Phase 1: Context gathering (Sonnet, parallel, `model: "sonnet"`)

Each agent gets the facts already established in this session (architecture, confirmed bugs below) so it does not re-derive them, and writes its brief to `Report/briefs/<name>.md`.

### Task 1: Unread-code brief (agent A)
- [ ] Read `evaluation/*.py`, `tests/`, `run_optimizer.py`, `run_agent.py`, `agent_framework/message_protocol.py`, `agent_registry.py`, `src/message_logger.py`, `src/reporting/exporters.py`.
- [ ] Answer in `Report/briefs/code_unread.md`: does `evaluation/generate_report.py` already batch-run the TCs and can the harness reuse it? Which tests exist and do they pass (`pytest tests -q`)? Does any code path use real message passing?
- Check: file exists, includes a "reuse / don't reuse" verdict for `generate_report.py`.

### Task 2: Existing-docs brief (agent B)
- [ ] Read `FINAL_20_PAGE_REPORT.md`, `20_PAGE_REPORT_PLAN.md`, `Technical Deliverlables and Documents/{Architecture_Document.md,Phase2_Integration_Report.md,literature_survey.md}`, `README_AGENT_FRAMEWORK.md`.
- [ ] Write `Report/briefs/docs.md`: reusable related-work prose with citations; a list of every claim contradicting the code (Z3, real message passing, speedup figures).
- Check: contradictions list has a `file:line` for the doc claim and for the code.

### Task 3: Test-suite inventory (agent C)
- [ ] Write `Report/briefs/testsuite.md`: table TC → bug category → expected finding type(s) → matching SOL file (or `none`); covers TC01-TC57, `TestCase1_Lr_errors.cpp`, the duplicate TC19.
- Check: every TC row has an expected-finding mapping; this table becomes `Report/experiments/expected_findings.json` in Task 5.

**Advisor checkpoint 1:** send briefs for review before Phase 3.

---

## Phase 2: User decision gate (blocks Phase 3)

Ask the user (see handoff). Default recommendation: fix **only the measurement instrument** (perf harness), measure everything else as-is, list the other bugs under Limitations. Fixing strength reduction / off-by-one before measuring changes the system under test; if the user wants that, run before/after for an ablation table.

### Task 4: Fix perf harness (only if approved)

**Files:** Modify `src/verification/perf_benchmarker.py:31-51`; Test `tests/test_perf_benchmarker.py`.

**Produces:** `PerfBenchmarker.benchmark(original_src, optimized_src) -> PerfResult` with `error is None` for a plain `int main()` program.

- [ ] **Step 1: Write failing tests** `test_benchmark_int_main_no_args` and `test_benchmark_int_main_argc_argv`: both use a 2,000,000-iteration sum loop; assert `result.error is None` and `result.original_ms > 0`.
- [ ] **Step 2:** Run `pytest tests/test_perf_benchmarker.py -v`; expected FAIL with `Original compilation failed.`
- [ ] **Step 3:** In `_TIMING_HARNESS` start with `#undef main`; make the wrapper call `__orig_main__` correctly for both zero-arg and `(argc, argv)` signatures (e.g. overloaded helper `_call_orig`).
- [ ] **Step 4:** Re-run the tests; expected PASS. Also expose numeric `speedup_pct`, `original_ms`, `optimized_ms` in the dict returned by `VerificationAgent.process` (`verification_agent.py:197`), so the harness can read them.

---

## Phase 3: Experiment harness (TDD) and runs

### Task 5: Harness core

**Files:** Create `evaluation/paper_experiments.py`, `Report/experiments/expected_findings.json`; Test `tests/test_paper_experiments.py`.

**Produces:**
- `run_case(path: str, config: str) -> dict` (keys: `tc, config, findings_types, transformations, ver_status, sec_status, stage_timings, speedup_pct, llm_fallback, original_compile_error`)
- `score_detection(findings_types: list[str], expected: list[str]) -> bool`
- `aggregate(rows: list[dict]) -> dict` (detection rate, correction rate, FP rate, PASS/ROLLBACK counts, mean stage times)

- [ ] **Step 1:** Write failing tests: `test_score_detection_hit`, `test_score_detection_miss`, `test_aggregate_counts_rollback`, `test_run_case_rule_only_tc01` (asserts `uninitialized_variable` in findings and `llm_fallback is False` with `rule_only`).
- [ ] **Step 2:** Run; expected FAIL (module missing).
- [ ] **Step 3:** Implement. Configs: `rule_basic` (`pipeline.run`, LLM `_available=False`), `rule_orch` (`run_orchestrated`), `ollama_orch`, `gemini_orch`. Each config runs in a separate subprocess; pass `use_cache=False`; set `OptimizationAgent.output_dir` to `Report/experiments/opt_out/`.
- [ ] **Step 4:** Run; expected PASS. Smoke-run `rule_basic` on TC01-TC05, view JSON.

### Task 6: Metrics beyond detection

- [ ] **False positives:** run analysis + security on each SOL file; any finding of that TC's own class counts as an FP.
- [ ] **Correction:** bug class absent after optimization AND (optimized output == SOL output, or both noted `nondeterministic`).
- [ ] **Failure modes:** record counts for `original_compile_error`, `rollback`, `llm_fallback`.
- [ ] Test names: `test_false_positive_on_sol`, `test_correction_requires_absent_bug_class`.

### Task 7: Run and aggregate

- [ ] Check Ollama: `curl localhost:11434/api/tags`; check `GEMINI_API_KEY` presence; record environment (CPU/GPU, g++ 6.3.0, model tags, Python version) in `Report/experiments/environment.json`.
- [ ] Run `rule_basic` and `rule_orch` on the full set.
- [ ] Run `ollama_orch`: stratified subset (one TC per category) in the background, or the full set overnight (user's choice). Run `gemini_orch` only if a key is present; otherwise record `unavailable`.
- [ ] Write raw `Report/experiments/raw/<config>/<tc>.json` and `Report/experiments/summary_<config>.csv`.
- Check: row count per CSV equals TC count of the run; no row has an empty `ver_status` without an `error` field.

**Advisor checkpoint 2:** send CSV summaries + environment before drafting; ask whether results are publishable or need a rerun.

---

## Phase 4: Writing (forks of this session, so they inherit the code reading; they run on Sonnet)

### Task 8: Tables and figures
- [ ] `evaluation/make_paper_tables.py` converts CSVs to Markdown tables (`Report/experiments/tables.md`). Test: `test_table_row_matches_csv`.
- [ ] Mermaid diagrams for pipeline and refinement loop (sources: `pipeline.py:155-427`, `orchestrator_agent.py:96-180`, `refinement_agent.py:127-292`).

### Task 9: Draft `Report/DeepCompile_Paper.md`
- [ ] Fork per section group: (a) Abstract/Intro/Related Work, (b) Architecture/Methodology, (c) Setup/Results, (d) Advantages/Limitations/Threats/Conclusion.
- [ ] Limitations must include the confirmed bugs: unsafe strength reduction and off-by-one rewrites, literal divide-by-zero not detected, security-agent format-string false positives, refinement cannot use the LLM after cycle 1, caches ignore LLM setting, SSE 180 s timeout, all-or-nothing rollback.
- [ ] Threats to validity: 56 synthetic micro-benchmarks, regex-based detectors, `-O0` timing, single machine, empty stdin.

---

## Phase 5: Claim audit and advisor review

### Task 10: Audit
- [ ] Script `evaluation/audit_paper.py`: every number in the Results section appears in a file under `Report/experiments/`; fails otherwise. Test: `test_audit_flags_unknown_number`.
- [ ] Manual check: each architecture claim carries `file:line`; grep the paper for "Z3", "formal", "real-time message" and justify each hit.
- [ ] **Advisor checkpoint 3:** send the finished draft for a final review; apply fixes via Sonnet agents.

**Self-review notes:** spec coverage checked against the outline (each section has a drafting task); signatures consistent between Tasks 5-8; plan length is proportionate (one task per deliverable).

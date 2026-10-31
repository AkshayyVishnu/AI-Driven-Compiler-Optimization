# Brief: evaluation/, tests/, CLI entry points, message framework (read-only pass)

## 1. Batch evaluation scripts
**evaluation/generate_report.py** (432 lines) - batch-runs a HARD-CODED 8-case subset, not all 58.
- Cases: DEFAULT_CASES generate_report.py:31-40 (TC01,06,09,11,12,14,16,19). `--cases TC01 ...` only FILTERS this list (:386-395); cannot add other TCs.
- Args: `--no-llm`, `--out FILE`, `--cases PREFIX...` (:358-368). No backend choice (default LLMClient(), :373). Label "online (Qwen 2.5 Coder)" hard-coded (:412).
- Calls `pipeline.run(path)` (basic pipeline, NOT orchestrator/refinement) (:96).
- Metrics (RunMetrics :54-71): status, elapsed_s, #findings, #high, optimization_applied, #transformations, verification status, diff_passed, security status, total/new vulns, overall_risk, detection sources.
- Output: Markdown only -> `Technical Deliverlables and Documents/Phase2_Integration_Report.md` (:46-49, :422). No JSON/CSV.
- Weaknesses: "bug categories" inferred from FILENAME keywords (:162-176), not from findings. "Pass rate" = status=="success" fraction, not correctness vs ground truth.
- MISSING for paper: bugs-identified vs expected, bugs-corrected, speedup %. Speedup is never read from verification_report.

**evaluation/generate_week13_reports.py** (298 lines): 12 hard-coded cases EVAL_CASES (:24-37), always no_llm=True (:70-84), no CLI args (main :273). Runs BOTH `run_orchestrated(max_cycles=3, low_conf_threshold=0.8)` (:109) and baseline `run()` (:114). Writes 3 MD reports + evaluation/week13_results.json (per case: statuses, iteration_count, stop_reason, elapsed, basic_elapsed, findings, transformations, new_vulns, stage_timings).
- Existing JSON: TC01 orchestrated 10.8 s vs basic 0.005 s (verification parallel_checks_s 10.5 s). Do not compare these latencies naively (baseline is suspiciously fast; probably verification short-circuits or is skipped in basic run - unverified, worth checking).
- Uses `datetime.UTC` (:17) -> needs Python >= 3.11.

Others: build_final_dossier.py / build_pdf.py (document/PDF packaging), verify_deliverables.py (checks deliverable files exist) - not experiment tools.

**Verdict:** generate_report.py = reuse PARTLY (keep run_case/RunMetrics skeleton; replace DEFAULT_CASES with glob of MicroBenchmarks/Testcases/TC*, add --llm backend, JSON/CSV output, ground-truth labels, speedup). generate_week13_reports.py = reuse partly for the orchestrated-vs-baseline A/B and stage_timings/JSON idea. Neither provides the paper metrics as-is. MEMORY.md says 58 testcases; scripts cover only 8 / 12.

## 2. tests/ (9 files)
Files: test_agent_integration (209 lines, threaded toy agents), test_agents_week6 (CoT validator/Analysis/Optimization), test_context_manager, test_llm_and_parser, test_message_protocol, test_orchestration_reporting (orchestrator/reporting/domain rules), test_security_week8 (446 lines; cppcheck tests skipif not installed :319), test_sustainability_estimator, test_verification_week7.
`python -m pytest tests -q` (165 s): **3 failed, 126 passed, 2 skipped** (526 warnings, all datetime.utcnow deprecation).
Failures:
- test_agent_integration.py::TestAgentCommunication::test_multiple_agents_communication - `AssertionError: 0 not greater than 0` (test_agent_integration.py:164).
- test_agent_integration.py::TestAgentCommunication::test_registry_statistics - `AssertionError: 0 not greater than 0`.
- test_llm_and_parser.py::TestPromptTemplates::test_optimization_prompt_contains_findings - `'uninitialized_var' not found in 'Optimize and fix ...'` (rendered prompt says "No specific findings"; stale test or prompt-builder regression).
In a focused rerun a `TypeError: '<' not supported between instances of 'Message' and 'Message'` also surfaced (PriorityQueue tie on equal priority, base_agent.py:161): a real bug in the threaded path, flaky/timing dependent.
Skips: cppcheck-not-installed / missing TC file (test_security_week8.py:319, :389, :398).
Not tested: perf benchmarker linking, end-to-end speedup, any whole-Testcases regression.

## 3. Real message passing?
- Framework supports it: BaseAgent has queue.PriorityQueue (base_agent.py:58), worker thread (:65, :234), send_message -> registry.route_message (:108-140), receive_message enqueues (:146-165); AgentRegistry.route_message looks up receiver, calls receiver.receive_message under RLock, counts per-route stats (agent_registry.py:118-143); start_all/stop_all (:145-162).
- Exercised ONLY by toy TestAgents in tests/test_agent_integration.py (:99,125,148,174,198) and verify_framework.py:214 (start_all, sleep, assert). 2 of those tests fail today.
- The real pipeline does NOT use it: agents are registered (pipeline.py:119-122) but never started; `_route` docstring pipeline.py:132-137 says "We do NOT call registry.route_message() ... agent threads are not started ... unread PriorityQueue and cause heapq comparison errors on Message objects"; it only calls `msg_logger._on_message(msg)` (:150-151). Confirms established fact.
- MessageLogger (src/message_logger.py:102-245): attach() monkey-patches registry.route_message (:132-140) but that hook is dead in pipeline mode; capture actually comes via _on_message from _route. run_pipeline.py:209-216 wires both. `--save-messages` dumps JSON. app.py:80 has its own _QueueMessageLogger for SSE.
- watch_agents.py (273 lines): runs the pipeline with the logger and pretty-prints (same observer mechanism; flags --full, --no-llm).
=> Message logs are synthetic traces of direct calls. Paper should say "protocol messages logged/observed", not asynchronous inter-agent communication.

## 4. CLI differences
- run_pipeline.py (:91-135): full flow; default = ORCHESTRATED run. Flags `--no-llm`, `--no-security`, `--llm {ollama,gemini}`, `--show-messages/-m`, `--save-messages FILE`, `--basic-pipeline` (skip orchestrator/refinement), `--max-cycles N` (3), `--low-conf-threshold F` (0.8), `--export-md`, `--export-html`, -v/-q. Best for ablations: basic vs orchestrated, max-cycles, no-security, backend.
- run_optimizer.py (280 lines, flags :108-118): ContextManager + AnalysisAgent + OptimizationAgent only; NO verification, NO security, NO orchestrator. Flags `--no-llm`, `--gemini` (boolean), `--out PATH`, -v/-q. Writes optimized file (default into MicroBenchmarks/Generated_optimisation/OPT_*). Good for optimization-only / LLM-vs-rule ablation.
- run_agent.py (534 lines): subcommands analyze | optimize | verify | security (:464-490). verify/security take `--optimized OPT_FILE` (auto-detected from Generated_optimisation if omitted); verify has no --no-llm/--llm (:476-481). Good for per-agent ablation (e.g. security on original file for raw detection counts).
- Gotcha: backend flag is `--llm` in run_pipeline/run_agent but `--gemini` in run_optimizer.

## 5. Contradictions / extensions
- Top-level `agents/` directory (analysis, optimization, orchestrator, security, verification) is a DIVERGENT older copy of src/agents/ (all files differ; no refinement_agent.py). utils/ (compiler.py: g++ wrapper compile/run/compile_string; file_utils.py: read_cpp_file, list_test_cases :27, list_solutions :43) is imported only by that legacy dir (agents/verification_agent.py:12, agents/orchestrator_agent.py:18). Pipeline uses src.agents.* (pipeline.py:21-24). Do not describe agents/ or utils/ as the system.
- src/reporting/exporters.py (134 lines): renders ExplainabilityReport to terminal/Markdown/HTML(/JSON) - findings, transformations, verification and security verdicts, stop_reason, review_required, reasoning_summary; no speedup field. Used by run_pipeline --export-md/--export-html.
- verify_framework.py: manual script (not pytest) checking protocol/context/registry with toy agents; not evidence about the real pipeline.
- Confirms: perf_benchmarker.py:31 `_TIMING_PREFIX = "#define main __orig_main__\n"`.
- Caution: most of the 126 passing tests cover rule components and the unused async framework; passing count says little about end-to-end optimisation quality.
- Cost for batch experiments: full pytest 165 s; verification ~10 s/case with --no-llm (week13_results.json), so 58 orchestrated cases is roughly 10+ min without LLM; LLM runs much longer.

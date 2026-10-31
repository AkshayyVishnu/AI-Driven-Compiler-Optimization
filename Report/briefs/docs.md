# Docs Brief (context only; no source/doc files modified)
Read: FINAL_20_PAGE_REPORT.md (FR), 20_PAGE_REPORT_PLAN.md (PLAN), FINAL_SUBMISSION.md (FS), DOCUMENTATION_GUIDE.md (DG), README_AGENT_FRAMEWORK.md (RAF), Architecture_Document.md (AD), Phase2_Integration_Report.md (P2), literature_survey.md (LS; read first 400 lines, headings, gaps, conclusion, references).
Report/ holds only 3 PDFs (DeepCompile_20_Page_Report.pdf, PBL guideline and example PDFs); no md/txt, so not read.
Spot-checked code: llm_client.py defaults are qwen2.5-coder:7b and gemini-2.5-flash (docs match). optimization_agent.py:506-510 has `x*2 -> x<<1` regex rewrites (the unsafe family). Testcase dir has 59 entries.

## 1. REUSABLE MATERIAL
### Background prose (consistent with code)
- FR 4.1 source-to-source optimization: "exposes the transformed program to the developer as a first-class artifact... must handle the developer's trust concerns directly". C/C++ UB paragraph is a good intro.
- FR 3.3 three gaps (reliability / workflow / explainability): usable motivation framing.
- FR 4.4 regex CodeParser: "intentionally limited: it is not a full AST". Honest and matches code.
- FR 4.3 and AD 3.2 ContextManager: RLock, deepcopy ContextVersion snapshots, max_versions=10 FIFO, rollback re-saves restored state as a new version. AD 3.2 is more precise.
- FR 7.8 conflict priority: verification/security veto > correctness-preserving opt > cosmetic.
- FR 5.1 motivating example: `for (int i = 0; i <= n; i++) data[i] = i * 2;` (off-by-one).
- FR 9.13 failure taxonomy (9 classes: false positive, false negative, unsafe optimization, verification miss, security miss, refinement oscillation, orchestration conflict, toolchain failure, unsupported code path). Good home for "unsafe optimization" admission.
- AD 6.4 security design. Rule layer CWE map: gets CWE-242; scanf %s and printf(var) CWE-134; strcpy/strcat/sprintf CWE-676; UAF CWE-416. Heuristics H1-H7: taint CWE-120, unchecked malloc CWE-476, signed/unsigned CWE-195, malloc int overflow CWE-190, buffer loop write CWE-121, recursive big buffer CWE-674, global thread write CWE-362. New-vuln = set difference of finding TYPES ignoring line numbers; rollback only for high severity, source rule/heuristic, confidence >= 0.8. Verify against security_agent.py before citing.
- AD 4.3 CoT Validator as trust gate (JSON with reasoning_steps, conclusion, confidence clamped to [0,1]; invalid -> rule-only fallback). AD 4.1 Ollama params: temp 0.1, max tokens 2048, timeout 360 s, 2 retries.
- AD 9: honest note that the OPT_* file stays on disk after rollback.
- AD 10 limitations table (linear pipeline, Z3 only simple arithmetic, g++ required, binary security rollback): seed for Limitations.
- FR 6.6 positioning: "occupies a middle ground between purely rule-based toolchains and purely generative suggestion engines".
- LS "Research Gaps" (about lines 933-975): Formal Verification ("Most ML approaches lack correctness guarantees"), Interpretability, LLMs ("Recent LLMs (GPT, Codex) not yet fully explored for compiler optimization"), Multi-Agent Optimization (future direction). Dated (Feb 2026 survey); cites no LLM code-optimization or LLM-agent work.
- LS is a 15-paper survey of ML-for-compilers (AutoTVM, Ansor, MLGO, RL phase ordering, PolyGym, GNN pass order). Mostly tensor/ML-compiler, weakly relevant to source-level C/C++ LLM optimization. Related-work in FR 6.1-6.5 is generic: no named LLM-code-opt, static-analysis, or translation-validation systems (e.g. Alive2, CBMC, Infer, PIE). Needs real expansion.

### Citations as written (FLAG = fix before paper)
FR section 11:
[1] Alfred V. Aho, Monica S. Lam, Ravi Sethi, and Jeffrey D. Ullman, *Compilers: Principles, Techniques, and Tools*, 2nd ed., Pearson, 2006.
[2] Michael Wooldridge, *An Introduction to MultiAgent Systems*, 2nd ed., Wiley, 2009.
[3] Leonardo de Moura and Nikolaj Bjorner, "Z3: An Efficient SMT Solver," in *Tools and Algorithms for the Construction and Analysis of Systems*, 2008. (OK; TACAS, LNCS 4963. Awkward to cite if Z3 is not run.)
[4] James C. King, "Symbolic Execution and Program Testing," *Communications of the ACM*, vol. 19, no. 7, 1976.
[5] Roy Schwartz, Jesse Dodge, Noah A. Smith, and Oren Etzioni, "Green AI," *Communications of the ACM*, vol. 63, no. 12, 2020.
[6] Chris Cummins et al., "CompilerGym: Robust, Performant Compiler Optimization Tasks for Machine Learning," 2020. (FLAG: arXiv 2109.08267, 2021 / CGO 2022; year wrong.)
[7] E. Suresh Babu, *PBL Report Writing Guidelines*... and [8] "Project artifacts in `Technical Deliverlables and Documents/`..." (course/local items: drop for paper)
LS References (strings as written):
1. Wang, Z., & O'Boyle, M. F. P. (2018). Machine Learning in Compiler Optimisation. *Proceedings of the IEEE*, 106(11), 1879-1901. (good)
2. Li, M., Liu, Y., Liu, X., Sun, Q., You, X., Yang, H., ... & Qian, D. (2021). The Deep Learning Compiler: A Comprehensive Survey. *IEEE TPDS*, 32(3), 708-727. (good)
3. Chen, T., Zheng, L., Yan, E., Jiang, Z., Moreau, T., Ceze, L., ... & Krishnamurthy, A. (2018). Learning to Optimize Tensor Programs. *NeurIPS*. (good; LS section header says "USENIX OSDI / NeurIPS", inconsistent)
4. Zheng, L., Jia, C., Sun, M., Wu, Z., Yu, C. H., Haj-Ali, A., ... & Stoica, I. (2020). Ansor: Generating High-Performance Tensor Programs for Deep Learning. *USENIX OSDI*. (good)
5. Google Research. (2020). MLGO: Machine Learning Guided Compiler Optimizations. *arXiv preprint*. (FLAG: real paper is Trofin et al., arXiv 2101.04808, 2021)
6. Cummins, C., Petoumenos, P., Wang, Z., & Leather, H. (2020). Static Neural Compiler Optimization via Deep Reinforcement Learning. *IEEE Transactions on Computers*. (FLAG HIGH: that title is by Mammadli, Jannesari, Wolf, LLVM-HPC 2020; the LS DOI 10.1109/TC.2020.2970726 and "5-15% over -O3" look misattributed. Do not cite unchecked.)
7-8, 10-15: "PolyGym Contributors", "DAC. (2023)", "NACOS Authors", "Intel Corporation... oneDNN Graph", "Souffle Authors", "GNN Pass Order Authors", "PreTuner Authors", "Transferable GO Authors": placeholders, not citable. 9. Xie, Z., Wang, M., Ye, Z., Zhang, Z., & Fan, R. (2022). Graphiler... *MLSys* (plausible).

## 2. CLAIMS vs CODE (code is ground truth)
| Claim (doc, location) | What the code actually does | Sev |
|---|---|---|
| "AI-Driven Compiler Optimization with Formal Verification" (FS l.2); "Formal Verification Report: How Z3 SMT solver is used to prove equivalence" (DG l.40); "Hybrid Rule/LLM/Formal verification pipeline" (DG l.25) | Z3 verifier exists but is skipped (z3 not installed, out of scope); handles only single `return expr;` arithmetic. No formal proof is ever produced | HIGH |
| "Verified correct by DifferentialTester + Z3 + LLM" (AD l.59); TC11 flow "L2 Z3: extract return expr, prove equivalent -> PROVEN_EQUIVALENT" (AD l.845) | Illustrative only; Z3 skipped and TC11 has no suitable return expr | HIGH |
| FR 4.5 / 6.5 / 7.6: Z3 "provides symbolic support when the code shape is suitable"; "uses symbolic reasoning as one useful layer" | Hedged but implies an active layer; Z3 contributes to no reported result | HIGH |
| "structured inter-agent communication" (FR abstract); "communicates through a shared message schema" (FR 4.2); "frontend can stream those events live... reconstruct the decision path" (FR 7.4); "agents communicate via messages" (RAF l.207); "Agent-to-agent handoff" (AD 3.4); "message protocol... for multi-agent coordination" (FR 3.6) | Pipeline._route only logs Message objects; agents are called directly via process(). AD l.137 and l.214-217 admit this ("audit trail only"). Describe as audit-logged shared blackboard + direct calls | HIGH |
| "FIPA-like communication protocol" (PLAN 4); "Request -> Thought -> Response" (PLAN 7) | Not implemented; only REQUEST/RESPONSE/NOTIFICATION types, not routed | MED |
| "Correctness: Ensuring optimized code is semantically identical" (FS l.14); "Correctness Guarantee that DeepCompile offers" (PLAN 6) | No guarantee: diff test is one run, empty stdin, stdout compare (AD 7) | HIGH |
| Performance benchmarking "prevent acceptance of obviously worse transformations" (FR 7.6); "Speedup %" (DG l.50); bar charts Original vs Optimized (PLAN 9); abstract to include speedup (PLAN 2) | Perf harness never links; no valid speedup numbers exist. Claim none | HIGH |
| "correctness-style pass rate of 83.3 percent" (FR abstract, 9.4); P2 l.18 | "PASS" is a pipeline status, not proven correctness. Samples tiny (12; P2: 6 run, 2 skipped); no ground-truth labels | HIGH |
| "0 newly introduced vulnerabilities... strongest measured result" (FR 9.11) | Regex/heuristic detection; new-vuln = type-set difference ignoring lines; no recall measure. Absence of detection is not absence of vulnerability | HIGH |
| Refinement: "max 3 cycles", AD 11.2 failure-aware LLM prompt feeding Z3 counterexample back; FR 8.8/9.6 | Cycle 1 rule-only; cycle 2+ intended LLM-guided but the shared LLM client stays disabled after cycle 1, so refinement is effectively rule-only. Z3 counterexamples never exist. FR 9.6 itself shows 0 cases improved | HIGH |
| "applies conservative rule-based fixes" (FR 3.6, 7.3, abstract) | Strength reduction (`x*2 -> x<<1`) is unsafe, e.g. `a + b * 2 -> a + b << 1` (precedence); passes only because verification never exercises it | HIGH |
| FR 9.6: "orchestration improves governance more than raw pass count"; 10.1 orchestration "central contribution" | Orchestrator/Refinement improved 0 of 12 cases; contribution not supported by data | MED |
| 4-layer verification: "Any single failure triggers a rollback" (AD l.569) vs verdict code (AD l.608-612: perf regression = FAIL without rollback; LLM "advisory" l.602 but l.611 rolls back on LLM FAIL) | Internally inconsistent; check verification_agent.py | MED |
| "Safe-by-Design: Automatic context rollback on any verification failure" (FS l.46); rollback "core safety guarantee" (AD 9) | ContextManager.rollback restores in-memory state; OPT_* file is still written to disk (AD 9 admits). "Guarantee" too strong | MED |
| "Every change is accompanied by a Chain-of-Thought (CoT) reasoning report" (FS l.48) | No-LLM runs use a stub (confidence 0.5, AD 4.1); rule path has no real CoT | MED |
| "4-layered audit (Rules, Heuristics, LLM, cppcheck)" (FS l.28) | In P2 only rules + heuristics were active; cppcheck optional, LLM off in evidence runs | MED |
| Test counts: "16 test cases" (PLAN 9), "16+" (AD 13), FR eval 12 cases, P2 8 targeted/6 run; project notes say 58; dir has 59 entries (TC01-TC57 plus extras) | Inconsistent; state exact corpus size and which subset was evaluated | MED |
| "33% pass rate (Phase 2 benchmark)" (AD l.918) vs 83.3% (P2) | Docs contradict each other | MED |
| P2 "Top bug categories detected" includes strcpy, UAF, heap overflow, but table shows Findings 0 for TC12/TC16/TC19 | Analysis missed them (only security layer flagged): evidence of regex recall limits, not of detection | MED |
| AD title block "Proposed Architecture Pending"; sections 10-11 call Orchestrator, Refinement, Feedback Memory (11.3), parallel Security (11.5) "proposed" | Orchestrator/Refinement now exist; Feedback Memory and parallel security not built (verify). Do not present as implemented | MED |
| "Target: Correctness rate >= 95%" (DG l.49) | Not met (83.3%, FR 9.14 admits) | LOW |
| LLM models: Qwen 2.5 Coder 7B via Ollama; Gemini gemini-2.5-flash (AD 4, 13) | Match llm_client.py. FR never names models (just "optional LLM"). RAF l.211 lists Qwen integration as a "next step" (stale) | LOW |
| Sustainability estimate mWh / mg CO2e (FR 8.12) | Rule-based estimate from size and timings, not metering; frame as heuristic | LOW |
| "30-40% reduction in total pipeline time" via parallel security (AD l.1043) | Unmeasured proposal | LOW |
| RAF: demo "Analysis -> Optimization -> Verification"; Next Steps "Add Security, Refinement, Orchestrator... Z3... benchmarking" | Stale; those exist now | LOW |
| "Python 3.13", "React 18, Vite, Monaco" (AD 13, FR 8.1) | Not checked against requirements/package.json | LOW |

## 3. NUMBERS IN DOCS: ALL DO-NOT-REUSE (pre perf-harness fix, no ground truth)
FR (April 2026, deterministic no-LLM, 12 cases):
- Cases 12; PASS 10; ESCALATE 2; accepted ROLLBACK 0; new vulns 0; pass rate 83.3% (abstract, 9.4, 9.14)
- Latency: orchestrated avg 4.5553 s, median 3.0267 s; baseline pipeline avg 0.0025 s; analysis parse 0.0006 s, rule 0.0007 s; optimization rule 0.0006 s; verification parallel checks 4.2473 s; security 0.0032 s (FR 8.6, 9.5)
- Comparison: baseline success 10/12; orchestrated PASS 10/12; improved by refinement 0 (FR 9.6)
- Case studies (FR 9.7-9.10): TC01 PASS, 0 refinements; TC11 2 findings, 3 transformations, PASS; TC16 baseline rollback -> ESCALATE after 1 iteration (no_material_improvement); TC31 ESCALATE (same reason)
- Appendix C cases: TC01, 07, 11, 12, 14, 16, 20, 27, 31, 35, 39, 41
P2 (2026-04-19, offline, 35.2 s total): 8 targeted, 6 run (TC06, TC09 skipped); success 5/6 = 83.3%; rollbacks 1 (TC16); avg findings/file 0.7; findings 4 (all high); transformations 5; diff tests passed 4/6; sec vulns 3; new vulns 0; risk high 1 / medium 2 / none 3; per-file times TC01 4.37, TC11 1.24, TC12 14.21, TC14 1.23, TC16 1.25, TC19 12.91 s.
AD: "33% pass rate"; "LLM latency ~5-30 s per file"; "30-40% pipeline time reduction" (proposal).
LS external-paper figures (MLGO 7% size / 1.5% QPS; AutoTVM 2x CPU / 4x GPU; Ansor 3.8x / 2.6x / 1.7x; "Cummins" 5-15% over -O3; "500+ citations"): unverified secondary claims; re-check in the original papers.
Advice: regenerate everything with the fixed harness. Report counts rather than percentages for tiny samples, and add labeled ground truth before any precision/recall claim.

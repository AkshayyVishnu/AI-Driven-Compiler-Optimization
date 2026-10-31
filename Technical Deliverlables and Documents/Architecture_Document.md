# Architecture Document
## DeepCompile
### Multi-Agent Pipeline for Safe, Verified C/C++ Code Optimization

---

**Version:** 2.0 (Phase 2 — Weeks 6–8)
**Date:** March 2026
**Status:** Experimental Pipeline Operational | Proposed Architecture Pending

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture Diagram](#2-high-level-architecture-diagram)
3. [Core Framework Layer](#3-core-framework-layer)
   - 3.1 BaseAgent
   - 3.2 ContextManager
   - 3.3 AgentRegistry
   - 3.4 Message Protocol
4. [LLM & Reasoning Layer](#4-llm--reasoning-layer)
   - 4.1 LLMClient (Ollama / Qwen 2.5 Coder)
   - 4.2 GeminiLLMClient
   - 4.3 CoT Validator
5. [Pipeline Orchestration](#5-pipeline-orchestration)
6. [Agent Specifications](#6-agent-specifications)
   - 6.1 Analysis Agent
   - 6.2 Optimization Agent
   - 6.3 Verification Agent
   - 6.4 Security Agent
7. [Verification Sub-System](#7-verification-sub-system)
8. [Data Flow: End-to-End](#8-data-flow-end-to-end)
9. [Rollback Mechanism](#9-rollback-mechanism)
10. [Current Architecture — Limitations](#10-current-architecture--limitations)
11. [Proposed Final Architecture](#11-proposed-final-architecture)
12. [Component Dependency Map](#12-component-dependency-map)
13. [Technology Stack](#13-technology-stack)

---

## 1. System Overview

The **DeepCompile** is a multi-agent software system that takes raw C/C++ source code as input and produces verified, security-audited, optimized code as output. If any stage cannot guarantee correctness or safety, the system rolls back to the original source and reports the reason.

### Core Philosophy

- **Safe by default:** rollback is the standard response to uncertainty, not failure.
- **Offline-first:** every agent has a rule-based fallback that works without an LLM.
- **Layered trust:** LLMs may inform decisions but cannot unilaterally trigger destructive actions (e.g., rollback).
- **Auditable:** every finding is tagged with its source (rule / heuristic / llm / cppcheck) and a confidence score.

### Input / Output Contract

```
INPUT:  C/C++ source file (.cpp / .c)

OUTPUT (success):  Optimized .cpp file saved to MicroBenchmarks/Generated_optimisation/
                   Verified correct by DifferentialTester + Z3 + LLM
                   Security-cleared (no new high-severity vulnerabilities introduced)

OUTPUT (rollback): Original source retained unchanged
                   PipelineResult with status="rollback" + explanation of which
                   layer triggered rollback and why
```

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        COMPILER OPTIMIZATION PIPELINE                           │
│                                                                                 │
│  C++ Source ──► [Analysis] ──► [Optimization] ──► [Verification] ──► [Security]│
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     AGENT FRAMEWORK LAYER                                │   │
│  │                                                                          │   │
│  │   ┌────────────────┐   ┌──────────────────┐   ┌────────────────────┐    │   │
│  │   │  AgentRegistry │   │  ContextManager  │   │  Message Protocol  │    │   │
│  │   │  (routing)     │   │  (shared state + │   │  (JSON typed msgs  │    │   │
│  │   │                │   │   versioned +    │   │   priority queues) │    │   │
│  │   │                │   │   rollback)      │   │                    │    │   │
│  │   └────────────────┘   └──────────────────┘   └────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     LLM & REASONING LAYER                                │   │
│  │                                                                          │   │
│  │   ┌─────────────────────┐         ┌──────────────────────────────────┐  │   │
│  │   │  LLMClient          │         │  CoT Validator                   │  │   │
│  │   │  (Ollama/Qwen 2.5   │◄───────►│  Parses JSON from LLM output.   │  │   │
│  │   │   Coder 7B or       │         │  Validates: reasoning_steps,     │  │   │
│  │   │   Gemini Flash)     │         │  findings, conclusion, confidence│  │   │
│  │   │  Stub fallback      │         │  Rejects malformed output.       │  │   │
│  │   └─────────────────────┘         └──────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Framework Layer

### 3.1 BaseAgent

**File:** `agent_framework/base_agent.py`

All agents inherit from `BaseAgent`. It provides:

| Capability | Implementation |
|---|---|
| Message queue | `queue.PriorityQueue(maxsize=100)` — thread-safe |
| Lifecycle | `start()` → RUNNING → `stop()` → STOPPED, `reset()` → INITIALIZED |
| Message dispatch | `_handle_request()`, `_handle_response()`, `_handle_notification()` |
| Send messages | `send_message()` → routed via `AgentRegistry` |
| Receive messages | `receive_message()` → placed on priority queue |

**Lifecycle State Machine:**

```
INITIALIZED ──► start() ──► RUNNING ──► stop() ──► STOPPED
                                │
                                └──► reset() ──► INITIALIZED
                                │
                                └──► (exception) ──► ERROR
```

**Abstract methods agents must implement:**

```python
def get_capabilities(self) -> List[str]: ...  # declares what this agent can do
def process(self, input_data: Dict) -> Dict: ...  # main logic
```

**In pipeline mode:** agents are NOT started as threads. `process()` is called
directly and synchronously by the pipeline. The message queue and thread are
used only in standalone / async mode.

---

### 3.2 ContextManager

**File:** `agent_framework/context_manager.py`

The ContextManager is the **shared blackboard** for all agents. It is the only
shared mutable state in the system.

**Thread safety:** All operations are protected by `threading.RLock()`.

**Schema (initial state):**

```json
{
  "original_code":          null,
  "source_file":            null,
  "analysis_results":       {},
  "optimization_suggestions": [],
  "verification_status":    {},
  "security_findings":      [],
  "metadata":               {}
}
```

**Key API:**

| Method | Description |
|---|---|
| `set(key, value)` | Writes value; supports dot-notation (`analysis_results.complexity`) |
| `get(key, default)` | Reads value; supports dot-notation; returns deep copy |
| `append(key, value)` | Appends to a list key |
| `update(dict)` | Batch set multiple keys |
| `rollback(version_id=None)` | Restores prior version (default: previous snapshot) |
| `get_version_history()` | Returns list of version timestamps |
| `clear()` | Resets to empty schema, clears version history |
| `to_json()` | Serialises entire context to JSON string |

**Versioning mechanism:**

Every `set()` / `append()` / `update()` call (with `save_version=True`) creates
a new `ContextVersion` snapshot via `deepcopy`. Up to `max_versions=10` snapshots
are retained in a FIFO list. `rollback()` pops back to the second-to-last version,
then saves a new version at the restored state.

```
Version history after pipeline run:

v0  (initial clear)
v1  analysis_results written
v2  optimization_suggestions written
v3  verification_status written
v4  security_findings written

On rollback():  context ← v3 snapshot, saved as v5
```

---

### 3.3 AgentRegistry

**File:** `agent_framework/agent_registry.py`

Central directory for agent discovery and message routing.

| Method | Description |
|---|---|
| `register(agent)` | Registers agent; sets `agent._registry = self` |
| `route_message(message)` | Looks up receiver by ID; calls `receiver.receive_message(msg)` |
| `start_all()` | Calls `agent.start()` on all registered agents |
| `stop_all()` | Calls `agent.stop()` on all registered agents |
| `get_statistics()` | Returns per-agent health / message counts |

**Note:** In the current pipeline mode, `route_message()` is NOT called on the
critical path. The pipeline calls `agent.process()` directly. Messages are
created and logged via `MessageLogger` as an observer (audit trail only), not
routed through the queue, to avoid heapq comparison errors on non-started threads.

---

### 3.4 Message Protocol

**File:** `agent_framework/message_protocol.py`

Every inter-agent communication is a typed `Message` object:

```python
@dataclass
class Message:
    message_id:     str          # UUID4
    sender_id:      str
    receiver_id:    str
    message_type:   MessageType  # REQUEST | RESPONSE | NOTIFICATION
    payload:        Dict[str, Any]
    priority:       MessagePriority  # HIGH=0, MEDIUM=1, LOW=2
    timestamp:      str          # ISO-8601
    correlation_id: Optional[str]  # links response to its originating request
```

**Message types and their use in the pipeline:**

| Type | Used when |
|---|---|
| `REQUEST` | Pipeline asks an agent to perform work |
| `RESPONSE` | Agent reports results back to the pipeline |
| `NOTIFICATION` | Agent-to-agent handoff (e.g., analysis_complete → optimizer) |

**Priority queue ordering:** `(priority_int, message)` tuples. Comparison
falls back to `message_id` (UUID string) to avoid heap errors when priorities
are equal.

---

## 4. LLM & Reasoning Layer

### 4.1 LLMClient (Ollama / Qwen 2.5 Coder)

**File:** `src/llm/llm_client.py`

Primary LLM backend. Connects to a locally running Ollama instance.

| Parameter | Default |
|---|---|
| Model | `qwen2.5-coder:7b` |
| Endpoint | `http://localhost:11434/api/generate` |
| Temperature | `0.1` (low — deterministic, code-safe) |
| Max tokens | `2048` |
| Timeout | `360s` |
| Retries | `2` |

**Connectivity check:** On instantiation, `GET /api/tags` is called with a 3s
timeout. If unreachable, `_available = False` and all calls return the stub.

**Stub response (offline fallback):**

When Ollama is unavailable, `_stub_response()` returns a minimal well-formed
CoT JSON that passes the CoT Validator with empty findings and `confidence=0.5`:

```json
{
  "reasoning_steps": ["Step 1: ...", "Step 2: ...", "Step 3: <hint>"],
  "findings": [],
  "conclusion": "<hint>",
  "confidence": 0.5
}
```

This guarantees the rule-based pipeline path always produces a result.

---

### 4.2 GeminiLLMClient

**File:** `src/llm/llm_client.py` — `GeminiLLMClient` class

Alternative cloud backend using the Google Gemini API (`gemini-2.5-flash`).

| Requirement | Detail |
|---|---|
| Package | `pip install google-genai` |
| Config | `GEMINI_API_KEY` environment variable |
| Fallback | Same stub as LLMClient if key missing or API unavailable |

**Backend selection:**

```python
from src.llm.llm_client import make_llm_client
llm = make_llm_client("ollama")  # default
llm = make_llm_client("gemini")  # cloud
```

---

### 4.3 CoT Validator

**File:** `src/reasoning/cot_validator.py`

The CoT Validator is the **trust gate** between every LLM call and the rest of
the system. LLM output is never used raw.

**Validation pipeline:**

```
LLM raw text
     │
     ▼
Extract JSON (try markdown fences ```json ... ``` first, then raw)
     │
     ▼
Check required keys: { reasoning_steps, conclusion, confidence }
     │
     ▼
Validate types:
  - reasoning_steps: non-empty list
  - confidence: float in [0.0, 1.0]  (clamped if out-of-range)
  - conclusion: string
  - findings: list (optional, defaults to [])
  - optimized_code: string (optional, for OptimizationAgent)
  - verdict: string (optional, for VerificationAgent)
     │
     ▼
Return CoTResult(is_valid=True/False, ...)
```

If `is_valid=False`, the calling agent falls back to rule-based results only.
LLM failure is **logged** but never raised as an exception.

---

## 5. Pipeline Orchestration

**File:** `src/pipeline/pipeline.py` — `CompilerOptimizationPipeline`

The pipeline is the top-level orchestrator. It is NOT an agent itself — it is
a coordinator that calls agents synchronously in sequence.

**Instantiation:**

```python
pipeline = CompilerOptimizationPipeline(llm_client=LLMClient(), message_logger=None)
```

On construction:
1. Creates one `ContextManager` instance (shared by all agents)
2. Creates one `AgentRegistry` instance
3. Instantiates all 4 agents, passing the shared context
4. Registers all agents with the registry

**Execution — `pipeline.run(file_path)`:**

```
Step 1  Read source file from disk
        Clear ContextManager (reset for new file)

Step 2  Emit REQUEST message to analysis_1 (audit log)
        analysis_agent.process({"source_code": ..., "file_path": ...})
        Emit RESPONSE message from analysis_1 (audit log)

Step 3  Emit NOTIFICATION analysis_complete → optimization_1 (audit log)
        Emit REQUEST to optimization_1 (audit log)
        optimization_agent.process({"source_code": ..., "analysis_report": ...})
        Emit RESPONSE from optimization_1 (audit log)

Step 4  Emit NOTIFICATION optimization_complete → verification_1 (audit log)
        Emit REQUEST to verification_1 (audit log)
        verification_agent.process({"original_code": ..., "optimized_code": ...})
        Emit RESPONSE from verification_1 (audit log)

Step 5  Determine final_code:
          if ver_status == ROLLBACK/FAIL → scan original_code
          else                           → scan optimized_code
        Emit NOTIFICATION verification_complete → security_1 (audit log)
        Emit REQUEST to security_1 (audit log)
        security_agent.process({"original_code": ..., "optimized_code": final_code})
        Emit RESPONSE from security_1 (audit log)

Step 6  Determine overall status:
          if ver_status == ROLLBACK or sec_status == ROLLBACK → "rollback"
          elif ver_status == FAIL                             → "partial"
          else                                               → "success"

Return PipelineResult(status, analysis_report, optimization_report,
                       verification_report, security_report)
```

**`pipeline.run_string(source_code, label)`:** Writes code to a temp file,
calls `run()`, deletes temp file. Used in tests.

---

## 6. Agent Specifications

### 6.1 Analysis Agent

**File:** `src/agents/analysis_agent.py`
**Agent ID:** `analysis_1`
**Agent Type:** `analysis`

#### Purpose
Detect bugs, performance issues, and security vulnerabilities in C/C++ source code
before any transformation is attempted. Produces a structured findings report that
drives the Optimization Agent.

#### Processing Pipeline

```
source_code
     │
     ▼
CodeParser.parse_string()
  → ParseResult:
      line_count, functions[], loops[], nested_loops,
      uninitialized_vars[], array_accesses[], malloc_calls[], free_calls[]
     │
     ├──► Layer 1: Rule-Based Analysis (always runs)
     │      - Uninitialized variable detection
     │      - Buffer overflow: variable-index array access in loop
     │      - Off-by-one: loop condition uses <= instead of <
     │      - Nested loop O(n²) complexity
     │      - Memory leak: malloc_calls > free_calls
     │      - Division-by-zero: divisor variable assigned 0 in same scope
     │
     ├──► Layer 2: LLM Analysis (Qwen 2.5 Coder)
     │      Prompt: AnalysisPromptTemplate.build(source, file_path, parse_summary)
     │      System: "Expert C/C++ bug detector, respond in JSON CoT format"
     │      Output validated by CoTValidator
     │      On failure → [] (empty, rule-based only)
     │
     └──► Merge & Deduplicate
            Key: (finding_type, line_number)
            Rule-based findings take precedence; LLM findings added if unique
```

#### Output Schema

```python
{
  "file_path":       str,
  "rule_findings":   List[Finding],    # from rule-based layer
  "llm_findings":    List[Finding],    # from LLM layer (empty if offline)
  "all_findings":    List[Finding],    # merged, deduplicated
  "reasoning_steps": List[str],        # from CoT
  "conclusion":      str,
  "confidence":      float,            # [0.0, 1.0]
  "summary":         str,              # human-readable
  "parse_meta": {
    "line_count":       int,
    "functions":        List[str],
    "has_nested_loops": bool,
    "max_loop_depth":   int,
  }
}
```

#### Finding Schema

```python
{
  "type":        str,     # e.g. "buffer_overflow", "uninitialized_variable"
  "description": str,
  "line":        int | None,
  "severity":    str,     # "high" | "medium" | "low"
  "source":      str,     # "rule" | "llm"
}
```

#### Context Writes
- `context.set("analysis_results", result)`
- `context.set("original_code", source_code)`
- `context.set("source_file", file_path)`

---

### 6.2 Optimization Agent

**File:** `src/agents/optimization_agent.py`
**Agent ID:** `optimization_1`
**Agent Type:** `optimization`

#### Purpose
Transform the source code to fix detected issues and improve performance.
Reads the analysis report from context or from the passed `input_data`.

#### Processing Pipeline

```
source_code + analysis_report
     │
     ├──► Layer 1: Rule-Based Fixes (always runs)
     │      For each finding in all_findings:
     │        off_by_one_error / potential_buffer_overflow:
     │          Regex replace `<= N` → `< N` in for-loop conditions
     │        uninitialized_variable:
     │          Regex replace `type varname;` → `type varname = 0;`
     │
     ├──► Layer 2: LLM Transformation (Qwen 2.5 Coder)
     │      Prompt: OptimizationPromptTemplate.build(source, analysis_report)
     │      Expects CoT JSON with extra key: "optimized_code": "<full C++ source>"
     │      CoTValidator extracts cot.optimized_code
     │      If valid and different from source → use LLM code
     │      Otherwise → use rule-based code
     │
     └──► Generate unified diff (difflib.unified_diff)
          Save optimized file to MicroBenchmarks/Generated_optimisation/OPT_<filename>
```

#### Code Selection Logic

```
if llm_code is valid AND llm_code != original:
    final_code   = llm_code
    transforms   = rule_transforms + llm_transforms
else:
    final_code   = rule_code
    transforms   = rule_transforms
```

#### Output Schema

```python
{
  "file_path":       str,
  "original_code":   str,
  "optimized_code":  str,
  "unified_diff":    str,           # unified diff format
  "transformations": List[Dict],    # each: {type, description, severity}
  "reasoning_steps": List[str],
  "conclusion":      str,
  "confidence":      float,
  "output_file":     str,           # absolute path to saved file
  "summary":         str,
}
```

#### Context Writes
- `context.set("optimization_suggestions", result)`

---

### 6.3 Verification Agent

**File:** `src/agents/verification_agent.py`
**Agent ID:** `verification_1`
**Agent Type:** `verification`

#### Purpose
Verify that the optimized code is **semantically equivalent** to the original and
has not regressed in performance. Four independent verification layers are run in
sequence. Any single failure triggers a rollback.

#### 4-Layer Verification Architecture

```
original_code + optimized_code
     │
     ├──► Layer 1: DifferentialTester (diff_tester.py)
     │      Compile original → original.exe  (g++ -O0 -w)
     │      Compile optimized → optimized.exe
     │      Run both with empty stdin, 10s timeout
     │      Compare stdout byte-for-byte
     │      Result: DiffTestResult.passed = True | False | skipped
     │
     ├──► Layer 2: Z3 SMT Verifier (z3_verifier.py)
     │      Extract single `return <expr>;` from each function
     │      Declare symbolic Z3 Int variables for all identifiers
     │      Evaluate both expressions in Z3 context
     │      Add constraint: e1 != e2
     │      Solve: UNSAT → PROVEN_EQUIVALENT
     │              SAT  → COUNTEREXAMPLE_FOUND + model
     │              ----  → UNKNOWN (skipped for complex code)
     │      Gracefully skipped if z3-solver not installed
     │
     ├──► Layer 3: PerfBenchmarker (perf_benchmarker.py)
     │      Compile both with -O2 and timing wrappers
     │      Run 5 iterations each
     │      Compute mean runtime and speedup ratio
     │      Flags regression if optimized is significantly slower
     │
     └──► Layer 4: LLM Reasoning (VerificationPromptTemplate)
            Sends both code versions to Qwen with "are these semantically equivalent?"
            CoT validated; extracts verdict: "PASS" | "FAIL"
            LLM verdict is advisory — does not independently trigger rollback
```

#### Verdict Determination

```python
if not diff_result.passed:          → status = ROLLBACK
elif z3_result == COUNTEREXAMPLE:   → status = ROLLBACK
elif perf regression detected:      → status = FAIL (no rollback, just warn)
elif llm_verdict == FAIL:           → status = ROLLBACK
else:                               → status = PASS
```

#### Output Schema

```python
{
  "status":        str,    # "PASS" | "FAIL" | "ROLLBACK"
  "diff_passed":   bool,
  "z3_status":     str,    # "PROVEN_EQUIVALENT" | "COUNTEREXAMPLE_FOUND" | "UNKNOWN" | "SKIPPED"
  "perf_summary":  str,
  "llm_verdict":   str,
  "conclusion":    str,
  "summary":       str,
}
```

#### Context Writes
- On ROLLBACK: `context.rollback()` (reverts to pre-optimization snapshot)

---

### 6.4 Security Agent

**File:** `src/agents/security_agent.py`
**Agent ID:** `security_1`
**Agent Type:** `security`

#### Purpose
Audit the optimized code for security vulnerabilities using 4 independent layers.
Crucially, compare findings against the original code to identify vulnerabilities
**newly introduced** by the optimization. Only newly introduced, high-confidence
findings trigger a rollback.

#### 4-Layer Security Architecture

```
original_code + optimized_code
     │
     ├──► Layer 1: Rule-Based Scan (confidence 0.90)
     │      Pattern matching via exact regex on both code versions
     │
     │      Unsafe functions (CWE-mapped):
     │        gets()     → CWE-242 (unconditionally unsafe)
     │        scanf %s   → CWE-134 (unbounded string read)
     │        strcpy()   → CWE-676 (unbounded copy)
     │        strcat()   → CWE-676 (unbounded append)
     │        sprintf()  → CWE-676 (unbounded format output)
     │
     │      Format string bug:
     │        printf/fprintf/sprintf(variable, ...) → CWE-134
     │
     │      Use-after-free:
     │        free(ptr) / delete ptr / delete[] ptr
     │        followed by *ptr / ptr->field / ptr[i] in subsequent lines
     │        → CWE-416
     │
     ├──► Layer 2: Heuristic Multi-Signal Scan (confidence 0.65–0.85)
     │      7 independent heuristics, each produces score ∈ [0.0, 1.0]
     │
     │      H1 Taint Flow (threshold 0.50):
     │           input source (scanf/argv/fgets) + buffer sink (strcpy/memcpy)
     │           − guard (strlen/sizeof/snprintf) → CWE-120
     │
     │      H2 Unchecked malloc (threshold 0.60):
     │           malloc_count / null_check_count ratio → CWE-476
     │
     │      H3 Signed/Unsigned Mismatch (threshold 0.60):
     │           int variable used in malloc() size expr or array index → CWE-195
     │
     │      H4 Integer Overflow in malloc (threshold 0.70):
     │           malloc(a * b) without SIZE_MAX guard → CWE-190
     │
     │      H5 Buffer Loop Write (threshold 0.70):
     │           char buf[N] with for(; i < var ;) writing → CWE-121
     │
     │      H6 Recursive Large Buffer (threshold 0.60):
     │           recursive function with ≥1 KB local char buffer → CWE-674
     │
     │      H7 Global Thread Write (threshold 0.60):
     │           global var modified in thread-like function without mutex → CWE-362
     │
     ├──► Layer 3: LLM Semantic Scan (confidence capped at 0.70)
     │      SecurityPromptTemplate.build(optimized, original, baseline_types)
     │      CoT validated; LLM findings added to opt_all
     │      LLM findings tagged source="llm"
     │      LLM CANNOT independently trigger rollback
     │
     └──► Layer 4: cppcheck Static Analysis (confidence 0.85, optional)
            Detects availability: `cppcheck --version`
            Writes optimized code to temp file
            Runs: cppcheck --xml --xml-version=2 --enable=warning,error
            Parses XML output; maps cppcheck severity to high/medium/low
            Skipped gracefully if cppcheck not installed
```

#### New Vulnerability Detection

```python
orig_types = {f["type"] for f in orig_all_findings}
new_vulns  = [f for f in opt_all_findings if f["type"] not in orig_types]
```

Line numbers are intentionally ignored in this comparison because optimization
shifts code lines.

#### Rollback Decision

```python
rollback_triggers = [
    v for v in new_vulns
    if v["severity"] == "high"
    and v["source"] in ("rule", "heuristic")   # NOT "llm"
    and v["confidence"] >= 0.8
]
if rollback_triggers:
    context.rollback()
    status = "ROLLBACK"
else:
    status = "PASS"
```

#### Risk Classification

| Condition | Risk Level |
|---|---|
| No findings | `none` |
| Only low/medium severity | `low` or `medium` |
| ≥1 high severity finding | `high` |
| ≥3 high severity findings | `critical` |

#### Output Schema

```python
{
  "file_path":           str,
  "all_vulnerabilities": List[Vulnerability],
  "new_vulnerabilities": List[Vulnerability],
  "heuristic_scores":    Dict[str, float],   # per-signal transparency
  "overall_risk":        str,    # critical/high/medium/low/none
  "status":              str,    # "PASS" | "ROLLBACK"
  "rollback_triggers":   List[Vulnerability],
  "llm_reasoning":       List[str],
  "llm_conclusion":      str,
  "sources":             List[str],  # ["rules", "heuristics", "llm", "cppcheck"]
  "summary":             str,
}
```

---

## 7. Verification Sub-System

### DifferentialTester (`src/verification/diff_tester.py`)

Compiles and executes both versions of C++ code, comparing runtime output.

```
Compile original.cpp  ──► original.exe   (g++ -O0 -w, 10s timeout)
Compile optimized.cpp ──► optimized.exe
Run original.exe       ──► stdout_orig    (10s timeout, stdin=empty)
Run optimized.exe      ──► stdout_opt
Compare:  passed = (stdout_orig == stdout_opt)
```

Gracefully skips with `skipped=True` when `g++` is not on PATH.

### Z3 Verifier (`src/verification/z3_verifier.py`)

Formal equivalence checker for simple arithmetic functions.

```
1. Extract return expression from single-return functions
   (uses regex: r'\breturn\s+([^;{]+)\s*;')

2. Parse identifier names from both expressions
   (filters out C++ keywords)

3. Declare Z3 Int symbolic variables for each identifier

4. Evaluate both expressions in Z3 context using safe AST evaluator
   (only allows: BinOp, UnaryOp, Constant, Name, arithmetic ops)

5. Add constraint: expr1 != expr2
   Solver.check():
     UNSAT → PROVEN_EQUIVALENT for all inputs
     SAT   → COUNTEREXAMPLE_FOUND (model contains witness)
     else  → UNKNOWN
```

Returns `SKIPPED` if z3-solver package is not installed.

### PerfBenchmarker (`src/verification/perf_benchmarker.py`)

Measures and compares execution time of both code versions.

```
Compile with -O2 and timing wrappers
Run N=5 iterations each
Compute mean runtime in milliseconds
Speedup = original_time / optimized_time
Report: faster / same / slower with percentage
```

---

## 8. Data Flow: End-to-End

```
File: TC11_buffer_overflow_loop.cpp
──────────────────────────────────────────────────────────────────────────

STEP 1: ANALYSIS
  Input:  source_code (string)
  Rules:  detect off-by-one (i <= 10), variable array index
  LLM:    Qwen enriches with additional findings
  Output: all_findings = [
            {type: "off_by_one_error",          severity: "high",   line: 8},
            {type: "potential_buffer_overflow",  severity: "high",   line: 9},
          ]
  Context writes: analysis_results, original_code, source_file

STEP 2: OPTIMIZATION
  Input:  source_code + analysis_results (from context)
  Rules:  fix `i <= 10` → `i < 10` in for-loop
  LLM:    generates full corrected code
  Output: optimized_code (fixed), unified_diff, transformations=[off_by_one_fix]
  Saved:  MicroBenchmarks/Generated_optimisation/OPT_TC11_buffer_overflow_loop.cpp
  Context writes: optimization_suggestions

STEP 3: VERIFICATION
  Input:  original_code + optimized_code
  L1 DiffTest:  compile both, run, compare stdout → PASS
  L2 Z3:        extract return expr, prove equivalent → PROVEN_EQUIVALENT
  L3 Perf:      speedup measured → no regression
  L4 LLM:       "semantically equivalent? Yes" → PASS
  Status:       PASS
  Context writes: verification_status (no rollback)

STEP 4: SECURITY
  Input:  original_code + optimized_code
  L1 Rules:     no unsafe functions detected
  L2 Heuristic: taint_flow=0.0, buffer_loop=0.8 → unbounded_loop_write flagged
  L3 LLM:       no new vulnerabilities found
  L4 cppcheck:  (skipped if not installed)
  New vulns:    [] (buffer_loop_write was present in original too)
  Status:       PASS
  Risk:         none

FINAL STATUS: success
OUTPUT:  PipelineResult(status="success", ...)
         Optimized file saved at MicroBenchmarks/Generated_optimisation/OPT_TC11_*
```

---

## 9. Rollback Mechanism

The rollback mechanism is the system's core safety guarantee.

### When Rollback Triggers

| Stage | Trigger Condition |
|---|---|
| Verification — DiffTest | `stdout_original != stdout_optimized` |
| Verification — Z3 | `COUNTEREXAMPLE_FOUND` |
| Verification — LLM | `llm_verdict == "FAIL"` (CoT validated) |
| Security | New HIGH-severity finding from Layer 1 or Layer 2 with `confidence >= 0.80` |

### What Happens on Rollback

```
1. context.rollback() is called
   ├── Restores context._context to the previous ContextVersion snapshot
   └── Saves restored state as a new version (audit trail preserved)

2. final_code is set back to source_code (original, not optimized)

3. PipelineResult.status = "rollback"

4. Optimized file (if already saved) remains on disk but is clearly labeled OPT_*
   and the pipeline result makes the rollback explicit

5. The reason for rollback is recorded in:
   verification_report["summary"] or security_report["rollback_triggers"]
```

### Rollback Does NOT

- Modify or delete the saved OPT_* file (for debugging purposes)
- Re-run the analysis or optimization stages
- Retry the optimization with different parameters (this is a proposed improvement)

---

## 10. Current Architecture — Limitations

| Limitation | Impact | Proposed Fix |
|---|---|---|
| Linear pipeline — no retry on failure | A failed optimization triggers immediate rollback with no second attempt | Self-refinement loop (see Section 11) |
| Z3 scope limited to simple arithmetic expressions | Pointer logic, struct access, heap operations cannot be formally verified | Extend to symbolic execution (KLEE/Angr) in future |
| No cross-file learning | Each file is processed independently; patterns from prior runs are not remembered | Feedback memory / fine-tuning |
| LLM latency adds ~5–30s per file (when online) | Not suitable for batch processing at scale | Async parallel agent execution |
| g++ required for differential testing | On systems without g++, Layer 1 verification is skipped entirely | Containerised build environment |
| Security rollback is binary | One new high-severity vuln triggers full rollback even if fixable | Selective rollback per-finding type |
| No Orchestrator Agent | Agent execution order is hardcoded in `pipeline.py` | Orchestrator Agent (see Section 11) |
| 33% pass rate (Phase 2 benchmark) | Verification layer correctly rejects poor optimizations; optimizer needs smarter transforms | Improved prompt engineering + more rule-based fixes |

---

## 11. Proposed Final Architecture

The proposed final architecture transforms the current linear pipeline into a
**closed-loop learning system** with dynamic orchestration.

### 11.1 Orchestrator Agent (new)

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│                                                             │
│  Inputs: file_path, file metadata, risk profile             │
│                                                             │
│  Responsibilities:                                          │
│    1. Classify input file (type, complexity, known patterns)│
│    2. Select agent subset and execution order               │
│    3. Set verification strictness per file risk level       │
│    4. Monitor pipeline health and inject retries            │
│    5. Aggregate final PipelineResult                        │
│                                                             │
│  Example decisions:                                         │
│    Low-risk header-only file → skip security scan           │
│    High-complexity nested loops → increase Z3 timeout       │
│    Previously-failed pattern → pre-warn optimizer           │
└─────────────────────────────────────────────────────────────┘
```

### 11.2 Self-Refinement Loop (new)

```
CURRENT:
  Optimize → Verify → FAIL → Rollback (dead end)

PROPOSED:
  Optimize → Verify → FAIL
                        │
                        ▼
              Refinement Agent:
                Feed failure reason back to OptimizationAgent
                Attempt #2 with failure-aware prompt
                        │
                 ┌──────┴──────┐
               PASS          FAIL (attempt 2)
                │               │
              continue       Rollback
```

**Refinement prompt additions:**
- What transformation was attempted
- What verification layer failed and why
- Which counterexample the Z3 solver found
- Constraint: "do not re-apply the off-by-one fix; it caused a runtime regression"

### 11.3 Feedback Memory (new)

```
┌────────────────────────────────────────────────────────────┐
│                   FEEDBACK MEMORY STORE                    │
│                                                            │
│  Per transformation type, track:                           │
│    - historical_pass_rate                                  │
│    - common_failure_reasons                                │
│    - file_pattern_associations                             │
│                                                            │
│  Used by Orchestrator and Optimization agents to:          │
│    - Skip transformations with < 30% historical pass rate  │
│    - Increase verification strictness for risky patterns   │
│    - Surface warnings before transformation is applied     │
└────────────────────────────────────────────────────────────┘
```

### 11.4 Proposed Full Pipeline Diagram

```
C++ Source
    │
    ▼
┌───────────────────┐
│  ORCHESTRATOR     │──── reads Feedback Memory
│  AGENT            │──── classifies file
│                   │──── sets strategy
└────────┬──────────┘
         │ dispatches
         ▼
┌─────────────────────────────────────────────────────┐
│           CORE PIPELINE (controlled by Orchestrator) │
│                                                     │
│  [Analysis] ──► [Optimization] ──► [Verification]  │
│                        ▲                  │         │
│                        │      FAIL        │         │
│               [Self-Refinement] ◄─────────┘         │
│                        │      PASS (attempt 2)       │
│                        └──────────────────────►      │
│                                           [Security] │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────┐
│  FEEDBACK MEMORY  │◄── update with outcome
│  UPDATE           │
└────────┬──────────┘
         │
         ▼
    PipelineResult
    + Audit Log
    + Memory Update
```

### 11.5 Parallel Execution (proposed)

```
CURRENT:  Analysis → Opt → Verify → Security   (fully sequential)

PROPOSED: Analysis → Opt → Verify ─────────────────────────► merge
                             └──► Security (parallel thread)  │
                                                               ▼
                                                         Final Result
```

Verification (compilation-heavy) and Security (regex/heuristic) can run in
parallel threads sharing the same ContextManager (already thread-safe).
Estimated 30–40% reduction in total pipeline time.

---

## 12. Component Dependency Map

```
pipeline.py (CompilerOptimizationPipeline)
  ├── agent_framework.AgentRegistry
  ├── agent_framework.ContextManager
  ├── src.llm.llm_client.LLMClient
  ├── src.agents.AnalysisAgent
  │     ├── agent_framework.BaseAgent
  │     ├── src.parser.CodeParser
  │     ├── src.llm.prompt_templates.AnalysisPromptTemplate
  │     └── src.reasoning.CoTValidator
  ├── src.agents.OptimizationAgent
  │     ├── agent_framework.BaseAgent
  │     ├── src.llm.prompt_templates.OptimizationPromptTemplate
  │     └── src.reasoning.CoTValidator
  ├── src.agents.VerificationAgent
  │     ├── agent_framework.BaseAgent
  │     ├── src.verification.DifferentialTester   → g++ (external)
  │     ├── src.verification.Z3Verifier           → z3-solver (optional)
  │     ├── src.verification.PerfBenchmarker      → g++ (external)
  │     ├── src.llm.prompt_templates.VerificationPromptTemplate
  │     └── src.reasoning.CoTValidator
  └── src.agents.SecurityAgent
        ├── agent_framework.BaseAgent
        ├── src.llm.prompt_templates.SecurityPromptTemplate
        ├── src.reasoning.CoTValidator
        └── cppcheck (external, optional)
```

---

## 13. Technology Stack

| Component | Technology | Version / Notes |
|---|---|---|
| Language | Python | 3.13 |
| LLM (primary) | Qwen 2.5 Coder 7B | via Ollama, local, offline-capable |
| LLM (secondary) | Google Gemini Flash | 2.5-flash, cloud, requires API key |
| LLM runtime | Ollama | `http://localhost:11434` |
| Formal verifier | Z3 SMT Solver | `pip install z3-solver`, optional |
| Static analyzer | cppcheck | System binary, optional |
| C++ compiler | g++ (MinGW/MSYS on Windows, GCC on Linux) | Used by DiffTester and PerfBenchmarker |
| JSON parsing | Python stdlib `json` | — |
| Thread safety | Python stdlib `threading` | RLock, PriorityQueue, Event |
| Diff generation | Python stdlib `difflib` | unified_diff |
| Web frontend | React + Vite + Monaco Editor | For interactive UI (separate from pipeline) |
| Backend API | Flask (`app.py`) | Serves pipeline results to frontend |
| Benchmarks | MicroBenchmarks/Testcases/ | 16+ hand-crafted C++ test files |
| Generated output | MicroBenchmarks/Generated_optimisation/ | OPT_*.cpp files |

---

*Architecture Document — DeepCompile*
*Generated: March 2026 | Phase 2 Complete | Phase 3 (Self-Refinement) Pending*

# 20-Page Expansion Plan for PBL Final Report
## Project: DeepCompile — AI-Driven Compiler Optimization

This plan outlines how to expand the current `PBL_DETAILED_REPORT.md` into a comprehensive 20-page academic document.

---

### 1. Front Matter (2 Pages)
*   **Title Page:** Project title, student name, roll number, department, university logo, and date.
*   **Table of Contents:** Detailed list of all sections and subsections with page numbers.
*   **List of Figures/Tables:** Captions and page numbers for all diagrams and data tables.

### 2. Abstract (1 Page)
*   **Include:** A 500-word summary covering the problem, the specific multi-agent solution, the hybrid (Rule + LLM) methodology, and key quantitative results (success rates, speedup).
*   **Exclude:** Citations and excessive technical jargon that isn't defined later.

### 3. Introduction (2 Pages)
*   **Context:** Elaborate on the history of compiler optimization (peephole vs. global).
*   **Gaps in State of the Art:** Discuss why LLVM passes are conservative and why ChatGPT/Copilot cannot be trusted for systems-level code.
*   **Research Questions:** Explicitly list 3-4 questions (e.g., "How does a versioned context prevent data corruption in multi-agent environments?").
*   **Contributions:** Bulleted list of 5-6 specific technical contributions (e.g., "Developed a custom regex-based fact extractor for C++").

### 4. Background Information (2.5 Pages)
*   **Multi-Agent Systems (MAS):** Define the FIPA-like communication protocol used in the project.
*   **Formal Methods & SMT:** A deep dive into **Z3**. Explain how C++ expressions are translated into SMT-LIB logic for equivalence checking.
*   **Differential Testing:** Explain the theory of "Morphic Testing" and how we use binary execution as a ground-truth oracle.
*   **Large Language Models in Compilers:** Brief history of "Neural Compiler" research.

### 5. Motivation & Problem Definition (1.5 Pages)
*   **The "Reliability Gap":** Provide a code example of a common LLM hallucination in C++ (e.g., an off-by-one error in a pointer loop).
*   **Resource Constraints:** Why human review of every optimization is not scalable.
*   **Safety Requirements:** Why standard testing is insufficient for security-critical optimizations.

### 6. State of the Art / Related Work (1.5 Pages)
*   **Comparison Table:** Include a full-page table comparing **DeepCompile** vs. **LLVM -O3**, **GitHub Copilot**, and **CompilerGym**.
*   **Discussion:** Analyze why current tools fail to provide the "Correctness Guarantee" that DeepCompile offers.

### 7. Design of Solution (Architectural Design) (3.5 Pages)
*   **System Overview Diagram:** Describe a high-fidelity diagram showing the 3-tier architecture.
*   **Agent Interaction Protocol:** Describe the sequence of messages (Request -> Thought -> Response) between the Orchestrator and specialized agents.
*   **Context Manager & Versioning:** Explain the `save_state` and `rollback` logic. **Include a state transition diagram.**
*   **The 4-Layer Verification Stack:**
    *   L1: Differential Test (Execution).
    *   L2: Z3 SMT (Formal Logic).
    *   L3: Perf Benchmarking (Timing).
    *   L4: LLM Reasoning (Semantic).
*   **Security Audit Layers:** Detail the 7 security heuristics used (e.g., buffer length checks, pointer lifecycle tracking).

### 8. Realization of Solution (Methodology) (3 Pages)
*   **Implementation Stack:** Detailed versions of Python, Flask, React, g++, and Z3.
*   **The CodeParser Engine:** Explain the regex logic for extracting function signatures and loop bounds. **Include a code snippet of the core regex patterns.**
*   **Prompt Engineering:** Show the actual System Prompt templates used for the Optimization Agent.
*   **Frontend SSE Streaming:** Explain the technical implementation of streaming JSON fragments for live "Agent Thoughts" in the UI.

### 9. Validation / Evaluation of Solution (3 Pages)
*   **The Benchmark Suite:** Describe the 16 test cases in `MicroBenchmarks`.
*   **Detailed Case Studies (Include at least 3):**
    *   *Case 1: Uninitialized Variable.* Show Before/After code and the Agent's reasoning.
    *   *Case 2: Memory Leak.* Show how the agent injected `free()` and how the Security Agent verified it.
    *   *Case 3: Failed Optimization.* Show a case where the agent introduced a bug, and the Verification Agent triggered a rollback.
*   **Performance Charts:** Describe bar charts for "Execution Time: Original vs. Optimized."
*   **Security Risk Heatmap:** Describe a table showing the risk level of different test cases before and after the audit.

### 10. Conclusions & Future Work (1 Page)
*   **Summary:** Final verdict on the project's viability.
*   **Future Roadmap:** Discuss "Phase 3: Self-Refinement" and "Phase 4: Multi-File Projects."

### 11. References & Appendices (1 Page)
*   **References:** Use standard IEEE or APA format for all cited papers and tools.
*   **Appendix:** (Optional) Links to the repository and a sample raw log from a pipeline run.

---

### What to EXCLUDE:
*   **Code Dumps:** Do not include more than 20 lines of code at once. Use snippets.
*   **Repetitive Content:** Don't explain the 4-agent flow in every section. Explain it once in "Design" and refer back to it.
*   **Irrelevant UI Details:** Don't spend more than half a page on "button colors" or CSS. Focus on the *functionality* of the UI.

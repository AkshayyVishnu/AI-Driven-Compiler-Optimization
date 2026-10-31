/*
 * TC56_multi_rule_violations.cpp
 *
 * Deliberately buggy student grade processor.
 * Every rule-based check in AnalysisAgent should fire at least once.
 *
 * BUGS EMBEDDED (one per rule):
 *  Rule 1  — Uninitialized variable         : int total; used before assignment
 *  Rule 2  — Buffer overflow (var index)    : arr[i] accessed with variable index in loop
 *  Rule 3  — Off-by-one (<= instead of <)   : for (i <= SIZE)
 *  Rule 4  — Nested O(n^2) loops            : inner loop inside outer loop
 *  Rule 5  — Memory leak                    : 2 malloc, only 1 free
 *  Rule 6  — Division by zero risk          : divisor = 0 then x / divisor
 *  Rule 7  — Type mismatch (str -> int)     : int status = "active"
 *  Rule 8  — Loop-invariant strlen          : strlen(name) inside nested loop
 *  Rule 9  — Redundant constant in loop     : int threshold = 50 inside loop
 *  Rule 10 — sizeof inside loop             : sizeof(grades) inside loop
 *  Rule 11 — Empty if body                  : if (score < 0) { }
 *  Rule 12 — Empty else body                : } else { }
 *  Rule 13 — Dead code after return         : statement after return at same indent
 */

    #include <iostream>
    #include <cstring>
    #include <cstdlib>

    #define SIZE 10

    /* ── helper: classify a score ─────────────────────────────────────────────── */

    const char* classify(int score) {
        if (score >= 90) {
            return "Distinction";
        }
        if (score >= 50) {
            return "Pass";
        }
        return "Fail";
        std::cout << "classification done" << std::endl;   // Rule 13: dead code after return
    }

    /* ── helper: compute ratio ─────────────────────────────────────────────────── */

    int ratio(int a, int b) {
        return a / b;           // b may be 0 — called with divisor below (Rule 6 context)
    }

    /* ── main processing function ─────────────────────────────────────────────── */

    int main() {

        /* Rule 7 — type mismatch: string literal assigned to int */
        int status   = "active";
        int category = "pass";

        /* Rule 1 — uninitialized variable: total used before any assignment */
        int total;
        int preliminary = total + 100;      // total is uninitialized here

        /* Rule 6 — division by zero risk: divisor explicitly set to 0 */
        int divisor = 0;
        int scaled  = preliminary / divisor;

        /* Rule 5 — memory leak: grades malloc'd but never freed */
        int*  grades = (int*)  malloc(SIZE * sizeof(int));
        char* labels = (char*) malloc(SIZE * 32);
        free(labels);
        /* grades is never freed — leak */

        /* Rule 3 — off-by-one: i <= SIZE writes grades[10] (index 0..10 = 11 items) */
        for (int i = 0; i <= SIZE; i++) {
            grades[i] = i * 10;             /* Rule 2 — variable index in loop */
        }

        /* Rule 11 — empty if body */
        if (scaled < 0) { }

        /* Rule 4 — nested O(n^2) loops */
        char name[] = "StudentRecord";

        for (int i = 0; i < SIZE; i++) {
            for (int j = 0; j < SIZE; j++) {

                /* Rule 8 — loop-invariant strlen: name never changes inside loop */
                int nameLen   = strlen(name);

                /* Rule 9 — redundant constant declaration inside loop */
                int threshold = 50;

                /* Rule 10 — sizeof inside loop: compile-time constant, needlessly repeated */
                int gradeBytes = sizeof(grades);

                if (grades[i] > threshold) {
                    grades[i] += nameLen + gradeBytes;
                } else { }              /* Rule 12 — empty else body */
            }
        }

        /* Rule 13 — dead code after return (in main) */
        return 0;
        std::cout << "Processing complete: " << total << std::endl;
    }

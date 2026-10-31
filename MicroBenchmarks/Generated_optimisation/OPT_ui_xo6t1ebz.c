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
        // [dead code] std::cout << "classification done" << std::endl;   // Rule 13: dead code after return
    }

    /* ── helper: compute ratio ─────────────────────────────────────────────────── */

    int ratio(int a, int b) {
        return a / b;           // b may be 0 — called with divisor below (Rule 6 context)
    }

    /* ── main processing function ─────────────────────────────────────────────── */

    int main() {

        /* Rule 7 — type mismatch: string literal assigned to int */
        const char* status = "active";
        const char* category = "pass";

        /* Rule 1 — uninitialized variable: total used before any assignment */
        int total = 0;
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
        for (int i = 0; i <= SIZE; ++i) {
            grades[i] = i * 10;             /* Rule 2 — variable index in loop */
        }

        /* Rule 11 — empty if body */

        /* Rule 4 — nested O(n^2) loops */
        char name[] = "StudentRecord";

        for (int i = 0; i < SIZE; ++i) {
            int nameLen   = strlen(name);
            int threshold = 50;
            int gradeBytes = sizeof(grades);
            for (int j = 0; j < SIZE; ++j) {

                /* Rule 8 — loop-invariant strlen: name never changes inside loop */

                /* Rule 9 — redundant constant declaration inside loop */

                /* Rule 10 — sizeof inside loop: compile-time constant, needlessly repeated */

                if (grades[i] > threshold) {
                    grades[i] += nameLen + gradeBytes;
                }
            }
        }

        /* Rule 13 — dead code after return (in main) */
        free(grades); /* fix: memory leak */
        return 0;
        // [dead code] std::cout << "Processing complete: " << total << std::endl;
    }
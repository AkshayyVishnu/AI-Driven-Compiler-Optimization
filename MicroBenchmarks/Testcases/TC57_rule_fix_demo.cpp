/*
 * TC57_rule_fix_demo.cpp
 *
 * Compact test case designed to trigger 4 rule-based auto-fixable errors.
 *
 * BUG SUMMARY
 * -----------
 *  Bug 1 — Uninitialized variable  (line 23) : int total;  used before assignment
 *  Bug 2 — Off-by-one error        (line 30) : i <= SIZE  should be i < SIZE
 *  Bug 3 — Unsafe strcpy           (line 37) : strcpy()   -> strncpy()
 *  Bug 4 — Uninitialized variable  (line 42) : int result; used before return
 *
 * All four bugs are detected by AnalysisAgent (rule-based / heuristics mode)
 * and can be auto-fixed by the "Fix" / "Fix All" button in the UI.
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define SIZE 5

/* ── compute_sum ────────────────────────────────────────────────────────────
   Bug 1: 'total' is declared but never initialized before use.
   The first iteration reads total + scores[0], which is undefined behaviour.
*/
int compute_sum(int scores[], int n) {
    int total;                        /* BUG 1 — uninitialized, should be: int total = 0; */
    for (int i = 0; i < n; i++) {
        total += scores[i];
    }
    return total;
}

/* ── fill_array ─────────────────────────────────────────────────────────────
   Bug 2: loop condition uses <= SIZE, writing scores[5] past the end of a
   SIZE-element array (off-by-one, classic CWE-193).
*/
void fill_array(int scores[]) {
    for (int i = 0; i <= SIZE; i++) { /* BUG 2 — off-by-one: should be i < SIZE */
        scores[i] = i * 10;
    }
}

/* ── copy_name ───────────────────────────────────────────────────────────────
   Bug 3: strcpy() copies src into a fixed 32-byte buffer with no length check.
   A long src string overflows the buffer (CWE-676).
*/
void copy_name(char* src) {
    char name[32];
    strcpy(name, src);                /* BUG 3 — unsafe: should be strncpy(name, src, sizeof(name)-1) */
    printf("Name: %s\n", name);
}

/* ── get_grade ───────────────────────────────────────────────────────────────
   Bug 4: 'result' is declared but never assigned before the conditional.
   If score < 0 the branch is skipped and 'result' holds a garbage value.
*/
int get_grade(int score) {
    int result;                       /* BUG 4 — uninitialized, should be: int result = 0; */
    if (score >= 50) {
        result = 1;
    }
    return result;                    /* undefined if score < 50 */
}

/* ── main ────────────────────────────────────────────────────────────────── */
int main() {
    int scores[SIZE];
    fill_array(scores);               /* triggers Bug 2 (off-by-one write) */

    int sum = compute_sum(scores, SIZE); /* triggers Bug 1 (uninitialized total) */
    printf("Sum: %d\n", sum);

    copy_name("Alice");               /* triggers Bug 3 (strcpy) */

    int grade = get_grade(75);        /* triggers Bug 4 (uninitialized result) */
    printf("Grade: %d\n", grade);

    return 0;
}

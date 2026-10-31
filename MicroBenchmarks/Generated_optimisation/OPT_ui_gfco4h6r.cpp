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
}

/* ── helper: compute ratio ─────────────────────────────────────────────────── */
int ratio(int a, int b) {
    return a / b;           // b may be 0 — called with divisor below (Rule 6 context)
}

/* ── main processing function ─────────────────────────────────────────────── */
int main() {
    int total = 0;
    int preliminary = total + 100;      // total is initialized here

    int divisor = 1; // Ensure divisor is not zero
    int scaled = preliminary / divisor;

    int* grades = (int*)malloc(SIZE * sizeof(int));
    char* labels = (char*)malloc(SIZE * 32);
    free(labels);

    for (int i = 0; i < SIZE; i++) {
        grades[i] = i * 10;
    }

    if (scaled < 0) { }

    char name[] = "StudentRecord";
    int nameLen = strlen(name);
    int threshold = 50;
    int gradeBytes = sizeof(grades);

    for (int i = 0; i < SIZE; i++) {
        grades[i] += nameLen + gradeBytes;
    }

    return 0;
}

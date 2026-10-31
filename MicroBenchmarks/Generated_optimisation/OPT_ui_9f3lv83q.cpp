#include <stdio.h>
#include <stdlib.h>

/* === SYNTAX + LOGIC ERRORS DEMO ===
Paste into DeepCompile and run the pipeline */

/* Initialized globals */
int globalScore = 0;
int callCount = 0;

/* Off-by-one + uninitialized local + memory leak fixed */
int compute_average(int n) {
    int total = 0;
    int* values = (int*)malloc(n * sizeof(int));

    for (int i = 0; i < n; i++) {
        if (i >= n) break;
        values[i] = i * 3;
        total += values[i];
    }

    free(values);
    return total / n;
}

/* Missing semicolons + uninitialized variable fixed */
int get_ratio(int input) {
    int divisor = 1; // Default value to avoid division by zero
    int result = input / divisor;

    if (result > 0) {
        printf("Result is positive: %d\n", result);
    }

    return input / divisor;
}

/* Division by zero fixed */
float compute_rate(int events) {
    int duration = 1; // Default value to avoid division by zero
    return (float)events / duration;
}

int main() {
    int score = 0;
    printf("Score: %d\n", score);

    char label[32] = "Default Label";
    printf("Label: %s\n", label);

    int avg = compute_average(10);
    int ratio = get_ratio(avg);

    printf("Global: %d\n", globalScore);
    printf("Calls : %d\n", callCount);

    float rate = compute_rate(50);
    printf("Rate  : %.2f\n", rate);

    return 0;
}
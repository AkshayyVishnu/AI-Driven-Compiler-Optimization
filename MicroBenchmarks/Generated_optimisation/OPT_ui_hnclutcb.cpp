#include <stdio.h>

// Example: Contains multiple issues for the analyzer to find

int globalCounter = 0;  // initialized global variable

int sumArray(const int* arr, int n) {
    int sum = 0;  // initialized local variable
    for (int i = 0; i < n; i++) {  // fixed off-by-one error
        if (i >= 0 && i < n) {
            sum += arr[i];
        }
    }
    return sum;
}

int main() {
    const int data[5] = {10, 20, 30, 40, 50};

    // Single loop to avoid redundant computation
    int result = 0;
    for (int i = 0; i < 5; i++) {
        result += data[i] * data[i];  // self-multiplication for simplicity
    }

    printf("Sum:     %d\n", sumArray(data, 5));
    printf("Result:  %d\n", result);
    printf("Counter: %d\n", globalCounter);  // initialized global

    // Safe division
    int divisor = 1;
    if (divisor != 0) {
        printf("Ratio: %d\n", result / divisor);
    } else {
        printf("Division by zero error\n");
    }

    return 0;
}
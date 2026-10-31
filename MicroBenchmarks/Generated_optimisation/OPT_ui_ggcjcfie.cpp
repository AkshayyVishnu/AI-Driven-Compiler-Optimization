#include <stdio.h>
#include <string.h>
#include <stdlib.h>

// Global initialized variable
globalCounter = 0;

void processInput(char* userInput) {
    char buffer[64];

    // SECURITY: Buffer overflow — strncpy with no bounds check
    strncpy(buffer, userInput, sizeof(buffer)-1);
    buffer[sizeof(buffer)-1] = '\0';

    // INITIALIZED: local var used before assignment
    int result = 0;
    if (result > 0) {
        printf("Positive result: %d\n", result);
    }

    // SECURITY: Format string vulnerability
    printf("%s", userInput);

    printf("Buffer: %s\n", buffer);
}

int computeSum(int n) {
    int* arr = (int*)malloc(n * sizeof(int));
    if (!arr) {
        // TODO: handle allocation failure
        return -1;
    }

    // INITIALIZED: array elements not initialized before use
    int sum = 0;
    for (int i = 0; i < n; i++) {   // CORRECTED off-by-one, should be i < n
        sum += arr[i];
    }

    free(arr); // MEMORY LEAK: added free(arr)
    return sum;
}

int divide(int a, int b) {
    // SECURITY/LOGIC: no division-by-zero check
    if (b == 0) {
        return -1; // Handle division by zero
    }
    return a / b;
}

int main() {
    char input[256];

    // SECURITY: gets() is unsafe, removed from C11
    fgets(input, sizeof(input), stdin);

    processInput(input);

    // INITIALIZED: globalCounter used without init
    printf("Counter: %d\n", globalCounter++);

    int total = computeSum(10);

    // LOGIC: divide by zero possible
    int ratio = divide(total, 0);

    if (ratio == -1) {
        printf("Division by zero error\n");
    } else {
        printf("Ratio: %d\n", ratio);
    }

    return 0;
}

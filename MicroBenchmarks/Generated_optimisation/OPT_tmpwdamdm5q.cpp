#include <stdio.h>

int main() {
    int x = 0; // Initialized 'x' to prevent uninitialized variable use
    int divisor = 1; // Changed 'divisor' from 0 to 1 to prevent division by zero
    printf("%d %d\n", x, 1 / divisor);
    return 0;
}

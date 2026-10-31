
#include <stdio.h>
int main() {
    int x = 0; // Initialized 'x' to prevent uninitialized variable use
    char buf[5];
    // buf[10] = 'A'; // Removed: This line caused a buffer overflow as buf has size 5.
    printf("%d\n", x); // Added newline for better output formatting
    return 0;
}

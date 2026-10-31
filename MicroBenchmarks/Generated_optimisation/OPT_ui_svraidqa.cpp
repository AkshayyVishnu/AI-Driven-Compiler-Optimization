#include <stdio.h>
  #include <string.h>
  #include <stdlib.h>

  // Global uninitialized variable
  int globalCounter = 0;

  void processInput(char* userInput) {
      char buffer[64];

      // SECURITY: Buffer overflow — strcpy with no bounds check
      strncpy(buffer, userInput, sizeof(buffer)-1);
    buffer[sizeof(buffer)-1] = '\0'; /* fix: strcpy -> strncpy */

      // UNINITIALIZED: local var used before assignment
      int result = 0;
      if (result > 0) {
          printf("Positive result: %d\n", result);
      }

      // SECURITY: Format string vulnerability
      printf("%s", userInput;

      printf("Buffer: %s\n", buffer);
  }

  int computeSum(int n) {
      int* arr = (int*)malloc(n * sizeof(int));
      if (!arr) {
          /* TODO: handle allocation failure */
          return -1;
      } /* fix: unchecked malloc */

      // UNINITIALIZED: array elements not initialized before use
      int sum = 0;
      for (int i = 0; i <= n; ++i) {   // LOGIC: off-by-one, should be i < n
          sum += arr[i];
      }

      // MEMORY LEAK: no free(arr)
      return sum;
  }

  int divide(int a, int b) {
      // SECURITY/LOGIC: no division-by-zero check
      return a / b;
  }

  int main() {
      char input[256]
      // SYNTAX: missing semicolon above

      // SECURITY: gets() is unsafe, removed from C11
      fgets(input, sizeof(input), stdin);

      processInput(input);

      // UNINITIALIZED: globalCounter used without init
      printf("Counter: %d\n", globalCounter++);

      int total = computeSum(10);

      // LOGIC: divide by zero possible
      int ratio = divide(total, 0);

      printf("Ratio: %d\n", ratio)
      // SYNTAX: missing semicolon above

      return 0
      // SYNTAX: missing semicolon above
  }
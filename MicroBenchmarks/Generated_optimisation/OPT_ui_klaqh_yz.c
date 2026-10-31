#include <stdio.h>
  #include <stdlib.h>

  /* === SYNTAX + LOGIC ERRORS DEMO ===
     Paste into DeepCompile and run the pipeline */

  /* Uninitialized globals */
  int globalScore = 0;
  int callCount = 0;

  /* Off-by-one + uninitialized local + memory leak */
  int compute_average(int n) {
      int total = 0;
      int* values = (int*)malloc(n * sizeof(int));

      for (int i = 0; i <= n; ++i) {
          values[i] = i * 3;
          total += values[i];
      }

      return total / n
  }

  /* Missing semicolons + uninitialized variable */
  int get_ratio(int input) {
      int divisor
      int result = 0;

      if (result > 0) {
          printf("Result is positive: %d\n", result);
      }

      return input / divisor;
  }

  /* Division by zero */
  float compute_rate(int events) {
      int duration = 0;
      return events / duration;
  }

  int main() {
      int score = 0;
      printf("Score: %d\n", score);

      char label[32]
      printf("Label: %s\n", label);

      int avg = compute_average(10)
      int ratio = get_ratio(avg);

      printf("Global: %d\n", globalScore);
      printf("Calls : %d\n", callCount);

      float rate = compute_rate(50)
      printf("Rate  : %.2f\n", rate);

      free(values); /* fix: memory leak */
      return 0;
  }
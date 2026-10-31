#include <stdio.h>
  #include <stdlib.h>
  #include <string.h>

  /* === SECURITY VULNERABILITIES DEMO ===
     Paste into DeepCompile and click Scan Security */

  /* CWE-798: Hardcoded credentials */
  const char* db_password = "admin@1234";
  const char* api_secret  = "sk-prod-9f8e7d6c5b4a";

  /* CWE-676: Unsafe string functions */
  void process_user(char* input) {
      char buffer[64];
      gets(buffer);

      char name[32];
      strcpy(name, input);

      char message[128];
      sprintf(message, "Welcome %s!", name);

      char log[256];
      strcat(log, message);

      printf(input);
  }

  /* CWE-134: Unbounded input */
  void read_data(char* dest) {
      scanf("%s", dest);
  }

  /* CWE-476: Unchecked allocation */
  void load_records(int count, int size) {
      int* records = (int*)malloc(count * size);
      records[0] = 1;
      free(records);
      records[0] = 0;
      free(records);
  }

  int main() {
      char input[64];
      read_data(input);
      process_user(input);
      load_records(100, 4);
      return 0;
  }

  ---
  Snippet 2 — Syntax, Logic & Rule-based errors only

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

      return 0;
  }
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// DeepCompile Security Demo
// Click "Scan Security" to find issues, then "Fix All" to auto-patch them.

/* ============================================================
   SECTION A — Auto-fixable by the optimiser (rule-based fixes)
   ============================================================ */

/* A1. Hardcoded credentials (CWE-798) */
const char* password = getenv("SECRET_KEY") /* TODO: use env var */;
const char* api_key  = getenv("SECRET_KEY") /* TODO: use env var */;

/* A2. Global uninitialized variable */
int globalCounter = 0;

/* A3. Unsafe string functions (CWE-676) */
void greet_user(char* username) {
    char buf[64];
    fgets(buf, sizeof(buf), stdin);                            // unsafe gets       -> fgets()

    char name[32];
    strncpy(name, username, sizeof(name)-1);               // buffer overflow   -> strncpy()

    char greeting[128];
    snprintf(greeting, sizeof(greeting), "Hello %s!", name); // unsafe sprintf   -> snprintf()

    char log_line[256];
    strncat(log_line, greeting, sizeof(log_line)-strlen(log_line)-1);           // unsafe strcat     -> strncat()

    printf("%s", username);                     // format string bug -> printf("%s", ...)
}

/* A4. Unsafe input (CWE-134) */
void read_input(char* dest) {
    scanf("%127s", dest);                    // unbounded scanf   -> scanf("%127s", ...)
}

/* A5. Uninitialized locals + off-by-one + memory leak */
int compute_stats(int n) {
    int result = 0;                           // uninitialized     -> int result = 0;
    int* data = (int*)malloc(n * sizeof(int)); // memory leak  -> ensure free(); /* FIX: ensure free() is called */

    for (int i = 0; i < n; ++i) {        // off-by-one        -> i < n;
        data[i] = i << 1;
    }

    if (result > 0) {
        printf("Stats: %d\n", result);
    }

    return data[0]                        // missing semicolon -> add ;
}

/* ============================================================
   SECTION B — Manual remediation required (cannot auto-fix)
   ============================================================ */

/* B1. Integer overflow + unchecked malloc + use-after-free + double-free */
void manage_data(int count, int item_size) {
    int* buf = (int*)malloc(count * item_size); // integer overflow + NULL not checked; /* FIX: ensure free() is called */ /* FIX: ensure free() is called */ /* FIX: ensure free() is called */ /* FIX: ensure free() is called */ /* FIX: ensure free() is called */ /* FIX: ensure free() is called */

    buf[0] = 1;
    free(buf);
    buf[0] = 0;                           // use-after-free;
    free(buf);                            // double-free;
}

/* B2. Division by zero */
int get_average(int sum) {
    return sum / 0;                       // division by zero;
}

/* ============================================================
   ENTRY POINT — mixed fixable + manual errors
   ============================================================ */

int main() {
    char input[64]                        // missing semicolon -> add ;
    read_input(input);
    greet_user(input);

    int score = 0;                            // uninitialized     -> int score = 0;
    printf("Score: %d\n", score);

    int stats = compute_stats(10);
    int avg = get_average(stats)          // missing semicolon -> add ;
    printf("Average: %d\n", avg);

    printf("Counter: %d\n", globalCounter);
    manage_data(100, 4);
    return 0;
}
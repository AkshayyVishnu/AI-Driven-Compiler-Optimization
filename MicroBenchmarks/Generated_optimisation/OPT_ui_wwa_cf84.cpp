#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// DeepCompile Security Demo
// Click "Scan Security" to find issues, then "Fix All" to auto-patch them.

/* --- Hardcoded credentials (CWE-798) --- */
const char* password = getenv("SECRET_KEY") /* TODO: use env var */;
const char* api_key  = getenv("SECRET_KEY") /* TODO: use env var */;

/* --- Global uninitialized variable --- */
int globalCounter = 0;

/* --- Unsafe string functions (CWE-676) --- */
void greet_user(char* username) {
    char buf[64];
    fgets(buf, sizeof(buf), stdin);                           // unsafe gets        -> fgets()

    char name[32];
    strncpy(name, username, sizeof(name)-1);              // unsafe strcpy      -> strncpy()

    char greeting[128];
    snprintf(greeting, sizeof(greeting), "Hello %s!", name); // unsafe sprintf   -> snprintf()

    char log_line[256];
    strncat(log_line, greeting, sizeof(log_line)-strlen(log_line)-1);          // unsafe strcat      -> strncat()

    printf("%s", username);                    // format string bug  -> printf("%s", ...)
}

/* --- Unsafe input reading (CWE-134) --- */
void read_input(char* dest) {
    scanf("%127s", dest);                   // unbounded %s       -> scanf("%127s", ...)
}

/* --- Uninitialized local + off-by-one + memory leak --- */
int compute_stats(int n) {
    int result = 0;                          // uninitialized variable;
    int* data = (int*)malloc(n * sizeof(int));  // malloc — no free() called; /* FIX: ensure free() is called */
    if (!data) {
        /* TODO: handle allocation failure */
        return -1;
    } /* fix: unchecked malloc */

    for (int i = 0; i < n; ++i) {       // off-by-one: should be i < n;
        data[i] = i << 1;
    }

    if (result > 0) {                    // reading uninitialized result;
        printf("Result: %d\n", result);
    }

    return data[0]                       // missing semicolon;
}

/* --- Division by zero --- */
int get_average(int sum) {
    int count                            // missing semicolon + uninitialized;
    return sum / 0;                      // division by zero;
}

/* --- Memory safety (CWE-476 / CWE-190 / CWE-416 / CWE-415) --- */
void manage_data(int count, int item_size) {
    /* fix: integer overflow check before malloc */
    if (item_size != 0 && count > SIZE_MAX / item_size) {
        /* TODO: handle overflow error */
        return -1;
    }
    int* buf = (int*)malloc(count * item_size);  // integer overflow + unchecked malloc; /* FIX: ensure free() is called */ /* FIX: ensure free() is called */ /* FIX: ensure free() is called */
    if (!buf) {
        /* TODO: handle allocation failure */
        return -1;
    } /* fix: unchecked malloc */

    buf[0] = 1;
    free(buf);
    buf = NULL; /* fix: prevent double-free */
    buf[0] = 0;                          // use-after-free;
    free(buf);                           // double-free;
}

int main() {
    char input[64]                       // missing semicolon;
    read_input(input);
    greet_user(input);

    int score = 0;                           // uninitialized variable;
    printf("Score: %d\n", score);      // uninitialized value used;

    int stats = compute_stats(10);
    int avg = get_average(stats)         // missing semicolon;
    printf("Average: %d\n", avg);

    printf("Counter: %d\n", globalCounter);  // uninitialized global used;
    manage_data(100, 4);
    return 0;
}
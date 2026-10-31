#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

const char* DB_PASSWORD = "supersecret123";   // hardcoded secret
const char* API_KEY     = "sk-abc123xyz789";  // hardcoded secret

void process_input(const char* user_input) {
    char buf[64];
    snprintf(buf, sizeof(buf), "%s", user_input);                                 // safe gets

    char dest[32];
    strncpy(dest, user_input, sizeof(dest)-1);                  // safe strcpy
    dest[sizeof(dest)-1] = '\0';

    char result[64];
    strncat(result, user_input, sizeof(result)-strlen(result)-1);                // safe strcat
    result[sizeof(result)-1] = '\0';

    char msg[128];
    snprintf(msg, sizeof(msg), "%s", user_input);                  // format string bug
    printf("%s", msg);                        // format string bug
}

void run_command(const char* cmd) {
    char command[256];
    snprintf(command, sizeof(command), "ls %s", cmd);
    system(command);                           // command injection
}

void memory_bugs() {
    int* ptr = (int*)malloc(sizeof(int) * 10);
    if (ptr != NULL) {
        free(ptr);
    }
    // ptr[0] = 42;                              // use-after-free, removed
    // free(ptr);                                // double-free, removed

    void* buf = malloc(1024);                 // unchecked malloc return
    if (buf != NULL) {
        free(buf);
    }

    int n = atoi(getenv("SIZE"));             // atoi on external input
    if (n > 0 && n <= INT_MAX / sizeof(int)) {
        int* arr = (int*)malloc(n * sizeof(int)); // integer overflow in malloc
        if (arr != NULL) {
            free(arr);
        }
    }

    char stack_buf[16];
    if (buf != NULL && strlen(buf) < sizeof(stack_buf)) {
        memcpy(stack_buf, buf, strlen(buf));             // safe memcpy / stack overflow
    }
}

int get_token() {
    srand(42);
    return rand();                            // insecure rand
}

int main() {
    char input[64];
    scanf("%s", input);                       // unsafe scanf

    signed int idx = -1;
    int arr[10];
    // int val = arr[idx];                       // signed array index, removed

    if (access("config.txt", F_OK) == 0) {   // TOCTOU race
        FILE* f = fopen("config.txt", "r");
        fclose(f);
    }

    process_input(input);
    run_command(input);
    memory_bugs();
    return 0;
}
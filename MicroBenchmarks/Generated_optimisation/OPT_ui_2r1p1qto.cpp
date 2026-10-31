#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// TC56: Multi-rule security violations — click "Scan Security" to inspect

const char* DB_PASSWORD = "supersecret123";   // hardcoded secret
const char* API_KEY     = "sk-abc123xyz789";  // hardcoded secret

void process_input(char* user_input) {
    char buf[64];
    gets(buf);                                 // unsafe gets

    char dest[32];
    strcpy(dest, user_input);                  // unsafe strcpy

    char result[64];
    strcat(result, user_input);                // unsafe strcat

    char msg[128];
    sprintf(msg, user_input);                  // format string bug
    printf(user_input);                        // format string bug
}

void run_command(char* cmd) {
    char command[256];
    sprintf(command, "ls %s", cmd);
    system(command);                           // command injection
}

void memory_bugs() {
    int* ptr = (int*)malloc(sizeof(int) * 10);
    free(ptr);
    ptr[0] = 42;                              // use-after-free
    free(ptr);                                // double-free

    void* buf = malloc(1024);                 // unchecked malloc return

    // [dead code] int n = atoi(getenv("SIZE"));             // atoi on external input
    int* arr = (int*)malloc(n * sizeof(int)); // integer overflow in malloc

    char stack_buf[16];
    memcpy(stack_buf, buf, 1024);             // unsafe memcpy / stack overflow
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
    int val = arr[idx];                       // signed array index

    if (access("config.txt", F_OK) == 0) {   // TOCTOU race
        FILE* f = fopen("config.txt", "r");
        fclose(f);
    }

    process_input(input);
    run_command(input);
    memory_bugs();
    free(arr); /* fix: memory leak */
    free(buf); /* fix: memory leak */
    return 0;
}
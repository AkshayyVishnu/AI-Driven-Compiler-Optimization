#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// DeepCompile Security Demo
// Click "Scan Security" to find issues, then "Fix All" to auto-patch them.

/* --- Hardcoded credentials (CWE-798) --- */
const char* password = "hunter2secret";
const char* api_key  = "sk-live-abc123xyz";

/* --- Unsafe string functions (CWE-676) --- */
void greet_user(char* username) {
    char buf[64];
    gets(buf);                           // unsafe gets        -> fgets()

    char name[32];
    strcpy(name, username);              // unsafe strcpy      -> strncpy()

    char greeting[128];
    sprintf(greeting, "Hello %s!", name); // unsafe sprintf   -> snprintf()

    char log_line[256];
    strcat(log_line, greeting);          // unsafe strcat      -> strncat()

    printf(username);                    // format string bug  -> printf("%s", ...)
}

/* --- Unsafe input reading (CWE-134) --- */
void read_input(char* dest) {
    scanf("%s", dest);                   // unbounded %s       -> scanf("%127s", ...)
}

/* --- Memory safety (CWE-476 / CWE-190 / CWE-416 / CWE-415) --- */
void manage_data(int count, int item_size) {
    int* buf = (int*)malloc(count * item_size);  // integer overflow + unchecked malloc

    buf[0] = 1;
    free(buf);
    buf[0] = 0;                          // use-after-free
    free(buf);                           // double-free
}

int main() {
    char input[64];
    read_input(input);
    greet_user(input);
    manage_data(100, 4);
    return 0;
}
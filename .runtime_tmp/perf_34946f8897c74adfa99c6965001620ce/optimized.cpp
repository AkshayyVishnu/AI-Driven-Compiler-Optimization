#define main __orig_main__
// Category: Control Flow Errors
// Error: Infinite loop

#include <iostream>

int main() {
    int i = 0;
    
    while (i < 10) {
        std::cout << i << " ";
        // ERROR: Missing i++ increment - infinite loop
    }
    
    std::cout << std::endl;
    return 0;
}

#ifdef __cplusplus
#undef main
#include <chrono>
#include <cstdio>
// Overloads pick the right call for int main() and int main(int, char**).
static int _call_orig(int (*f)(int, char**), int c, char** v) { return f(c, v); }
static int _call_orig(int (*f)(), int, char**) { return f(); }
int main(int argc, char* argv[]) {
    auto _t0 = std::chrono::high_resolution_clock::now();
    int  _r  = _call_orig(__orig_main__, argc, argv);
    auto _t1 = std::chrono::high_resolution_clock::now();
    long long _ns = std::chrono::duration_cast<
        std::chrono::nanoseconds>(_t1 - _t0).count();
    fprintf(stderr, "__PERF_NS__:%lld\n", _ns);
    return _r;
}
#endif

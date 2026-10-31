// Category: Uninitialized Variables
// Error: Using uninitialized variable in arithmetic operation

#include <iostream>

int main() {
    int x = 0; // Bug fix: Initialize x to prevent undefined behavior
    const int y = 10; // Optimization: y is never modified, make it const
    
    const int result = x + y;  // Optimization: result is never modified, make it const
    std::cout << "Result: " << result << std::endl;
    
    return 0;
}

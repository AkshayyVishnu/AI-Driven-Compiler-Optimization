// Category: Array/Buffer Errors
// Error: Buffer overflow in loop

#include <iostream>

int main() {
    int arr[5];
    
    for (int i = 0; i <= 5; i++) {  // ERROR: Off-by-one, writes to arr[5]
        arr[i] = i * 2;
    }
    
    return 0;
}

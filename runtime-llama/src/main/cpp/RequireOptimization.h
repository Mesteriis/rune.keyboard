#pragma once

// Forced into every native translation unit by the parent CMake directory.
// Checking the compiler's effective mode catches missing flags and a trailing
// -O0 override in llama/ggml, not just the optimization of Rune's JNI wrapper.
#if !defined(__OPTIMIZE__) || __OPTIMIZE__ == 0
#error "Rune native runtime requires optimized compilation, including debug builds"
#endif

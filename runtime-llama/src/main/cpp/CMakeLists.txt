cmake_minimum_required(VERSION 3.31.6)
project(rune_llama LANGUAGES C CXX)

# The keyboard's debug APK is also used for real typing. Unoptimized ggml kernels
# cost seconds and excessive CPU per word. Keep debug symbols/assertions, but
# optimize the entire dependency tree, including C quantization kernels.
add_compile_options("$<$<CONFIG:Debug>:-O2>"
    "SHELL:-include \"${CMAKE_CURRENT_LIST_DIR}/RequireOptimization.h\"")

set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(GGML_NATIVE OFF CACHE BOOL "" FORCE)
set(GGML_OPENMP OFF CACHE BOOL "" FORCE)
set(GGML_BACKEND_DL OFF CACHE BOOL "" FORCE)
set(GGML_CPU_ALL_VARIANTS OFF CACHE BOOL "" FORCE)
set(GGML_CPU_KLEIDIAI OFF CACHE BOOL "" FORCE)
set(GGML_LLAMAFILE OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_COMMON OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_SERVER OFF CACHE BOOL "" FORCE)

get_filename_component(RUNE_SOURCE_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../.." REALPATH)
include("${CMAKE_CURRENT_LIST_DIR}/PrepareLlamaSource.cmake")
prepare_rune_llama_source("${RUNE_SOURCE_ROOT}" "${CMAKE_CURRENT_LIST_DIR}/patches/tokenizer-abort.patch")
add_subdirectory("${RUNE_LLAMA_SOURCE}" "llama" EXCLUDE_FROM_ALL)

# One scoring implementation shared by the evaluator and Android runtime.
add_library(rune_scoring STATIC "${RUNE_SOURCE_ROOT}/tools/eval/smart-typing-0.3/scoring.cpp")
target_compile_features(rune_scoring PRIVATE cxx_std_17)
target_compile_options(rune_scoring PRIVATE -Wall -Wextra -Werror -fvisibility=hidden)
target_compile_definitions(rune_scoring PRIVATE RUNE_TOKENIZER_ABORT=1)
target_include_directories(rune_scoring PUBLIC "${RUNE_SOURCE_ROOT}/tools/eval/smart-typing-0.3")
set_target_properties(rune_scoring PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_link_libraries(rune_scoring PUBLIC llama)

add_library(rune_llama SHARED rune_llama_jni.cpp)
target_compile_features(rune_llama PRIVATE cxx_std_17)
target_compile_options(rune_llama PRIVATE -Wall -Wextra -Werror -fvisibility=hidden)
target_link_libraries(rune_llama PRIVATE rune_scoring)

# Keep the only dynamic JNI entry point; methods register through JNI_OnLoad.
target_link_options(rune_llama PRIVATE "-Wl,--version-script=${CMAKE_CURRENT_LIST_DIR}/rune_llama.exports")
set_property(TARGET rune_llama APPEND PROPERTY LINK_DEPENDS "${CMAKE_CURRENT_LIST_DIR}/rune_llama.exports")

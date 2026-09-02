cmake_minimum_required(VERSION 3.31.6)
project(rune_native_scoring_contracts LANGUAGES C CXX)

get_filename_component(REPO_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." REALPATH)
set(runtime "${REPO_ROOT}/runtime-llama/src/main/cpp")
set(core "${REPO_ROOT}/tools/eval/smart-typing-0.3")
include("${runtime}/PrepareLlamaSource.cmake")
prepare_rune_llama_source("${REPO_ROOT}" "${runtime}/patches/tokenizer-abort.patch")

set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
foreach(option LLAMA_BUILD_COMMON LLAMA_BUILD_TESTS LLAMA_BUILD_TOOLS LLAMA_BUILD_EXAMPLES
    LLAMA_BUILD_SERVER LLAMA_BUILD_APP GGML_METAL GGML_CUDA GGML_VULKAN GGML_OPENMP
    GGML_NATIVE GGML_BACKEND_DL GGML_CPU_KLEIDIAI GGML_LLAMAFILE GGML_CCACHE)
    set(${option} OFF CACHE BOOL "" FORCE)
endforeach()
add_subdirectory("${RUNE_LLAMA_SOURCE}" llama EXCLUDE_FROM_ALL)

function(scoring_test target)
    target_compile_features(${target} PRIVATE cxx_std_17)
    target_compile_options(${target} PRIVATE -Wall -Wextra -Werror)
    target_include_directories(${target} PRIVATE "${runtime}" "${core}"
        "${RUNE_LLAMA_SOURCE}/include" "${RUNE_LLAMA_SOURCE}/src"
        "${RUNE_LLAMA_SOURCE}/ggml/include")
endfunction()

# This target supplies deterministic model calls, but always compiles the real
# shared scoring implementation and runtime wire encoder.
add_executable(scoring-contracts scoring_contract_test.cpp "${core}/scoring.cpp")
scoring_test(scoring-contracts)
target_compile_definitions(scoring-contracts PRIVATE RUNE_TOKENIZER_ABORT=1)

add_library(rune_scoring_contract_core STATIC "${core}/scoring.cpp")
scoring_test(rune_scoring_contract_core)
target_compile_definitions(rune_scoring_contract_core PRIVATE RUNE_TOKENIZER_ABORT=1)
target_link_libraries(rune_scoring_contract_core PUBLIC llama)
add_executable(scoring-math-test "${core}/scoring_math_test.cpp")
scoring_test(scoring-math-test)
target_link_libraries(scoring-math-test PRIVATE rune_scoring_contract_core)

add_executable(make-tokenizer-fixture make_tokenizer_fixture.cpp)
scoring_test(make-tokenizer-fixture)
target_link_libraries(make-tokenizer-fixture PRIVATE llama)
add_executable(tokenizer-abort-test tokenizer_abort_test.cpp)
scoring_test(tokenizer-abort-test)
target_link_libraries(tokenizer-abort-test PRIVATE llama)

enable_testing()
add_test(NAME scoring-contracts COMMAND scoring-contracts)
add_test(NAME scoring-math COMMAND scoring-math-test)
set(fixture "${CMAKE_CURRENT_BINARY_DIR}/synthetic-qwen2-vocab.gguf")
add_test(NAME tokenizer-fixture COMMAND make-tokenizer-fixture "${fixture}")
set_tests_properties(tokenizer-fixture PROPERTIES FIXTURES_SETUP tokenizer_fixture)
add_test(NAME tokenizer-abort COMMAND tokenizer-abort-test "${fixture}" --synthetic)
set_tests_properties(tokenizer-abort PROPERTIES FIXTURES_REQUIRED tokenizer_fixture TIMEOUT 60)
set_tests_properties(scoring-contracts scoring-math tokenizer-fixture PROPERTIES TIMEOUT 30)

# Explicit opt-in only; no download, and no skipped model tests in ordinary CI.
set(RUNE_SCORING_MODEL "" CACHE FILEPATH "Exact locally supplied Rune GGUF for optional qualification")
if(RUNE_SCORING_MODEL)
    include("${CMAKE_CURRENT_LIST_DIR}/VerifyModel.cmake")
    verify_scoring_model("${RUNE_SCORING_MODEL}")
    add_executable(scoring-model-test "${core}/scoring_model_test.cpp")
    scoring_test(scoring-model-test)
    target_link_libraries(scoring-model-test PRIVATE rune_scoring_contract_core)
    add_executable(token-dump token_dump.cpp)
    scoring_test(token-dump)
    target_compile_definitions(token-dump PRIVATE USE_ABORT=1)
    target_link_libraries(token-dump PRIVATE llama)
    add_test(NAME scoring-model-oracle COMMAND "${CMAKE_COMMAND}"
        "-DMODEL=${RUNE_SCORING_MODEL}" "-DPROGRAM=$<TARGET_FILE:scoring-model-test>"
        -P "${CMAKE_CURRENT_LIST_DIR}/RunModelTest.cmake")
    add_test(NAME tokenizer-model-equivalence COMMAND "${CMAKE_COMMAND}"
        "-DMODEL=${RUNE_SCORING_MODEL}" "-DPROGRAM=$<TARGET_FILE:token-dump>"
        "-DOUTPUT=${CMAKE_CURRENT_BINARY_DIR}/model.tokens"
        -P "${CMAKE_CURRENT_LIST_DIR}/RunModelTest.cmake")
    add_test(NAME tokenizer-model-abort COMMAND "${CMAKE_COMMAND}"
        "-DMODEL=${RUNE_SCORING_MODEL}" "-DPROGRAM=$<TARGET_FILE:tokenizer-abort-test>"
        -P "${CMAKE_CURRENT_LIST_DIR}/RunModelTest.cmake")
    set_tests_properties(scoring-model-oracle tokenizer-model-equivalence tokenizer-model-abort
        PROPERTIES TIMEOUT 300 LABELS exact-model)
endif()

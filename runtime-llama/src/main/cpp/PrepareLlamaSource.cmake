# Never mutate the submodule: verify the pin, then patch a private archive copy.
function(prepare_rune_llama_source repository_root tokenizer_patch)
    find_package(Git REQUIRED)
    set(expected_upstream "36b10154383b60eb15baac2c7a40d2a5f784faa7")
    set(expected_patch "0a043ce8a57b8534ef2f409443d2dd6ecf00042bd9c2b661b31d94618eb4dc95")
    set(upstream "${repository_root}/runtime-llama/src/main/cpp/llama.cpp")
    execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${upstream}" rev-parse HEAD
        RESULT_VARIABLE code OUTPUT_VARIABLE revision OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
    if(NOT code EQUAL 0 OR NOT revision STREQUAL expected_upstream)
        message(FATAL_ERROR "Unexpected llama.cpp source revision")
    endif()
    execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${upstream}" status --porcelain=v1 --untracked-files=all
        RESULT_VARIABLE code OUTPUT_VARIABLE dirty ERROR_QUIET)
    if(NOT code EQUAL 0 OR NOT dirty STREQUAL "")
        message(FATAL_ERROR "llama.cpp source must be pristine")
    endif()
    execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${repository_root}" ls-tree HEAD runtime-llama/src/main/cpp/llama.cpp
        RESULT_VARIABLE code OUTPUT_VARIABLE gitlink OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
    if(NOT code EQUAL 0 OR NOT gitlink MATCHES "^160000 commit ${expected_upstream}[	]runtime-llama/src/main/cpp/llama.cpp$")
        message(FATAL_ERROR "llama.cpp gitlink does not match the reviewed pin")
    endif()
    file(SHA256 "${tokenizer_patch}" patch_sha)
    if(NOT patch_sha STREQUAL expected_patch)
        message(FATAL_ERROR "Tokenizer patch does not match the reviewed SHA256")
    endif()
    set(source "${CMAKE_CURRENT_BINARY_DIR}/rune-llama-patched-source")
    set(archive "${CMAKE_CURRENT_BINARY_DIR}/rune-llama-upstream.tar")
    execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${upstream}" archive --format=tar "${expected_upstream}"
        OUTPUT_FILE "${archive}" RESULT_VARIABLE code ERROR_QUIET)
    if(NOT code EQUAL 0)
        message(FATAL_ERROR "Cannot archive llama.cpp source")
    endif()
    # This fixed subdirectory belongs solely to this configure/build tree.
    file(REMOVE_RECURSE "${source}")
    file(MAKE_DIRECTORY "${source}")
    file(ARCHIVE_EXTRACT INPUT "${archive}" DESTINATION "${source}")
    execute_process(COMMAND "${CMAKE_COMMAND}" -E env "GIT_CEILING_DIRECTORIES=${CMAKE_CURRENT_BINARY_DIR}"
        "${GIT_EXECUTABLE}" -C "${source}" apply --check "${tokenizer_patch}"
        RESULT_VARIABLE code OUTPUT_QUIET ERROR_QUIET)
    if(NOT code EQUAL 0)
        message(FATAL_ERROR "Tokenizer patch does not apply to the archive copy")
    endif()
    execute_process(COMMAND "${CMAKE_COMMAND}" -E env "GIT_CEILING_DIRECTORIES=${CMAKE_CURRENT_BINARY_DIR}"
        "${GIT_EXECUTABLE}" -C "${source}" apply "${tokenizer_patch}"
        RESULT_VARIABLE code OUTPUT_QUIET ERROR_QUIET)
    if(NOT code EQUAL 0)
        message(FATAL_ERROR "Cannot patch the llama.cpp archive copy")
    endif()
    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/rune-llama-provenance.json"
        "{\"upstream\":\"${expected_upstream}\",\"tokenizer_patch_sha256\":\"${patch_sha}\"}\n")
    set(RUNE_LLAMA_SOURCE "${source}" PARENT_SCOPE)
endfunction()

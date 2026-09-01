package io.github.mesteriis.rune.runtime.llama

import java.io.File

enum class RuntimeErrorCode(val stableCode: Int) {
    OK(0),
    MODEL_NOT_FOUND(1),
    MODEL_LOAD_FAILED(2),
    NOT_LOADED(3),
    CONTEXT_CREATE_FAILED(4),
    TOKENIZE_FAILED(5),
    DECODE_FAILED(6),
    EMPTY_OUTPUT(7),
    INVALID_UTF8(8),
    CANCELLED(9),
    INTERNAL_ERROR(10),
    NATIVE_LIBRARY_UNAVAILABLE(11),
}

sealed interface ModelLoadResult {
    data class Success(val loadMillis: Long) : ModelLoadResult
    data class Failure(val code: RuntimeErrorCode) : ModelLoadResult
}

sealed interface ModelSelfTestResult {
    data class Success(
        val promptMillis: Long,
        val firstTokenMillis: Long,
    ) : ModelSelfTestResult
    data class Failure(val code: RuntimeErrorCode) : ModelSelfTestResult
}

interface LocalModelRuntime : AutoCloseable {
    fun load(modelFile: File): ModelLoadResult
    fun selfTest(): ModelSelfTestResult
    fun cancelCurrentOperation()
    fun unload()
    override fun close() = unload()
}

package io.github.mesteriis.rune.runtime.llama

import java.io.File
import java.util.concurrent.Executors

class LlamaLocalModelRuntime : LocalModelRuntime {
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread(task, "rune-llama-runtime").apply { priority = Thread.NORM_PRIORITY - 1 }
    }
    private val lifecycle = NativeHandleLifecycle(
        executor = executor,
        initialHandle = nativeCreate(),
        resetCancellationNative = ::nativeResetCancellation,
        cancelNative = ::nativeCancel,
        unloadNative = ::nativeUnload,
        destroyNative = ::nativeDestroy,
    )

    override fun load(modelFile: File): ModelLoadResult {
        if (!modelFile.isFile) return ModelLoadResult.Failure(RuntimeErrorCode.MODEL_NOT_FOUND)
        val values = when (
            val call = lifecycle.beginOperation { handle -> nativeLoad(handle, modelFile.absolutePath) }
        ) {
            is NativeCallResult.Completed -> call.value
            NativeCallResult.Cancelled -> return ModelLoadResult.Failure(RuntimeErrorCode.CANCELLED)
            NativeCallResult.Failed,
            NativeCallResult.Unavailable,
            -> return ModelLoadResult.Failure(RuntimeErrorCode.INTERNAL_ERROR)
        }
        val code = errorCode(values.getOrElse(0) { RuntimeErrorCode.INTERNAL_ERROR.stableCode.toLong() })
        return if (code == RuntimeErrorCode.OK) {
            ModelLoadResult.Success(values.getOrElse(1) { 0L })
        } else {
            ModelLoadResult.Failure(code)
        }
    }

    override fun selfTest(): ModelSelfTestResult {
        val values = when (val call = lifecycle.continueOperation(::nativeSelfTest)) {
            is NativeCallResult.Completed -> call.value
            NativeCallResult.Cancelled -> return ModelSelfTestResult.Failure(RuntimeErrorCode.CANCELLED)
            NativeCallResult.Failed,
            NativeCallResult.Unavailable,
            -> return ModelSelfTestResult.Failure(RuntimeErrorCode.INTERNAL_ERROR)
        }
        val code = errorCode(values.getOrElse(0) { RuntimeErrorCode.INTERNAL_ERROR.stableCode.toLong() })
        return if (code == RuntimeErrorCode.OK) {
            ModelSelfTestResult.Success(
                promptMillis = values.getOrElse(1) { 0L },
                firstTokenMillis = values.getOrElse(2) { 0L },
            )
        } else {
            ModelSelfTestResult.Failure(code)
        }
    }

    override fun cancelCurrentOperation() {
        lifecycle.cancel()
    }

    override fun unload() {
        lifecycle.cleanup { handle -> nativeUnload(handle) }
    }

    override fun close() {
        lifecycle.close()
    }

    private fun errorCode(raw: Long): RuntimeErrorCode =
        RuntimeErrorCode.entries.firstOrNull { it.stableCode.toLong() == raw } ?: RuntimeErrorCode.INTERNAL_ERROR

    private external fun nativeCreate(): Long
    private external fun nativeDestroy(handle: Long)
    private external fun nativeLoad(handle: Long, modelPath: String): LongArray
    private external fun nativeSelfTest(handle: Long): LongArray
    private external fun nativeResetCancellation(handle: Long)
    private external fun nativeCancel(handle: Long)
    private external fun nativeUnload(handle: Long)

    private companion object {
        init {
            System.loadLibrary("rune_llama")
        }
    }
}

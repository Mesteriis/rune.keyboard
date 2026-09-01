package io.github.mesteriis.rune.runtime.llama

import java.io.File
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class LlamaLocalModelRuntime : LocalModelRuntime {
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread(task, "rune-llama-runtime").apply { priority = Thread.NORM_PRIORITY - 1 }
    }
    private val closed = AtomicBoolean(false)
    @Volatile private var handle: Long = nativeCreate()

    override fun load(modelFile: File): ModelLoadResult {
        if (!modelFile.isFile) return ModelLoadResult.Failure(RuntimeErrorCode.MODEL_NOT_FOUND)
        val values = callNative { nativeLoad(handle, modelFile.absolutePath) }
            ?: return ModelLoadResult.Failure(RuntimeErrorCode.INTERNAL_ERROR)
        val code = errorCode(values.getOrElse(0) { RuntimeErrorCode.INTERNAL_ERROR.stableCode.toLong() })
        return if (code == RuntimeErrorCode.OK) {
            ModelLoadResult.Success(values.getOrElse(1) { 0L })
        } else {
            ModelLoadResult.Failure(code)
        }
    }

    override fun selfTest(): ModelSelfTestResult {
        val values = callNative { nativeSelfTest(handle) }
            ?: return ModelSelfTestResult.Failure(RuntimeErrorCode.INTERNAL_ERROR)
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
        val current = handle
        if (current != 0L) nativeCancel(current)
    }

    override fun unload() {
        callNative { nativeUnload(handle) }
    }

    override fun close() {
        if (!closed.compareAndSet(false, true)) return
        val current = handle
        if (current != 0L) {
            executor.submit {
                nativeUnload(current)
                nativeDestroy(current)
            }.get()
            handle = 0L
        }
        executor.shutdownNow()
    }

    private fun <T> callNative(block: () -> T): T? {
        if (closed.get() || handle == 0L) return null
        return runCatching { executor.submit(Callable(block)).get() }.getOrNull()
    }

    private fun errorCode(raw: Long): RuntimeErrorCode =
        RuntimeErrorCode.entries.firstOrNull { it.stableCode.toLong() == raw } ?: RuntimeErrorCode.INTERNAL_ERROR

    private external fun nativeCreate(): Long
    private external fun nativeDestroy(handle: Long)
    private external fun nativeLoad(handle: Long, modelPath: String): LongArray
    private external fun nativeSelfTest(handle: Long): LongArray
    private external fun nativeCancel(handle: Long)
    private external fun nativeUnload(handle: Long)

    private companion object {
        init {
            System.loadLibrary("rune_llama")
        }
    }
}

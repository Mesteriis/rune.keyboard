package io.github.mesteriis.rune.runtime.llama

import java.util.concurrent.Callable
import java.util.concurrent.CancellationException
import java.util.concurrent.ExecutionException
import java.util.concurrent.ExecutorService
import java.util.concurrent.Future
import java.util.concurrent.RejectedExecutionException

internal sealed interface NativeCallResult<out T> {
    data class Completed<T>(val value: T) : NativeCallResult<T>
    data object Cancelled : NativeCallResult<Nothing>
    data object Unavailable : NativeCallResult<Nothing>
    data object Failed : NativeCallResult<Nothing>
}

/** Owns admission and destruction for one opaque native runtime handle. */
internal class NativeHandleLifecycle(
    private val executor: ExecutorService,
    initialHandle: Long,
    private val resetCancellationNative: (Long) -> Unit,
    private val cancelNative: (Long) -> Unit,
    private val unloadNative: (Long) -> Unit,
    private val destroyNative: (Long) -> Unit,
) : AutoCloseable {
    private val monitor = Any()
    private var handle = initialHandle
    private var closed = false
    private var teardown: Future<*>? = null
    private var lastAdmittedCallId = 0L
    private var cancelledThroughCallId = 0L
    private var cancellationPending = false

    fun <T> beginOperation(block: (Long) -> T): NativeCallResult<T> =
        call(CallKind.BEGIN_OPERATION, block)

    fun <T> continueOperation(block: (Long) -> T): NativeCallResult<T> =
        call(CallKind.CONTINUE_OPERATION, block)

    fun <T> cleanup(block: (Long) -> T): NativeCallResult<T> =
        call(CallKind.CLEANUP, block)

    private fun <T> call(kind: CallKind, block: (Long) -> T): NativeCallResult<T> {
        val task = synchronized(monitor) {
            if (closed || handle == 0L) return NativeCallResult.Unavailable
            val admittedHandle = handle
            val callId = ++lastAdmittedCallId
            try {
                executor.submit(Callable {
                    runCatching {
                        val skipped = synchronized(monitor) {
                            when {
                                closed || handle != admittedHandle -> NativeCallResult.Unavailable
                                kind != CallKind.CLEANUP && callId <= cancelledThroughCallId -> {
                                    NativeCallResult.Cancelled
                                }
                                kind == CallKind.CONTINUE_OPERATION && cancellationPending -> {
                                    NativeCallResult.Cancelled
                                }
                                else -> {
                                    if (kind == CallKind.BEGIN_OPERATION) {
                                        resetCancellationNative(admittedHandle)
                                        cancellationPending = false
                                    }
                                    null
                                }
                            }
                        }
                        skipped ?: NativeCallResult.Completed(block(admittedHandle))
                    }.getOrElse { NativeCallResult.Failed }
                })
            } catch (_: RejectedExecutionException) {
                return NativeCallResult.Failed
            }
        }
        return awaitInterruptibly(task)
    }

    fun cancel() {
        synchronized(monitor) {
            if (!closed && handle != 0L) {
                cancelledThroughCallId = lastAdmittedCallId
                cancellationPending = true
                cancelNative(handle)
            }
        }
    }

    override fun close() {
        var ownsTeardown = false
        val task = synchronized(monitor) {
            teardown ?: run {
                closed = true
                val admittedHandle = handle
                handle = 0L
                if (admittedHandle != 0L) runCatching { cancelNative(admittedHandle) }
                executor.submit {
                    if (admittedHandle != 0L) {
                        try {
                            unloadNative(admittedHandle)
                        } finally {
                            destroyNative(admittedHandle)
                        }
                    }
                }.also {
                    teardown = it
                    ownsTeardown = true
                }
            }
        }
        awaitUninterruptibly(task)
        if (ownsTeardown) executor.shutdownNow()
    }

    private fun <T> awaitInterruptibly(task: Future<NativeCallResult<T>>): NativeCallResult<T> = try {
        task.get()
    } catch (_: InterruptedException) {
        Thread.currentThread().interrupt()
        NativeCallResult.Failed
    } catch (_: ExecutionException) {
        NativeCallResult.Failed
    } catch (_: CancellationException) {
        NativeCallResult.Failed
    }

    private fun awaitUninterruptibly(task: Future<*>) {
        var interrupted = false
        try {
            while (true) {
                try {
                    task.get()
                    return
                } catch (_: InterruptedException) {
                    interrupted = true
                } catch (_: ExecutionException) {
                    return
                }
            }
        } finally {
            if (interrupted) Thread.currentThread().interrupt()
        }
    }

    private enum class CallKind {
        BEGIN_OPERATION,
        CONTINUE_OPERATION,
        CLEANUP,
    }
}

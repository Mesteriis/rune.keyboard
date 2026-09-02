package io.github.mesteriis.rune.runtime.llama

/** Explicit opt-in: the exact qualification GGUF must already be in the test app's filesDir. */
@Target(AnnotationTarget.CLASS, AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
annotation class VerifiedModelOnly

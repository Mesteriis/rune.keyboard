package io.github.mesteriis.rune.runtime.llama

/** Separate manual opt-in; VerifiedModelOnly continues to select its one qualification test. */
@Target(AnnotationTarget.CLASS, AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
annotation class RuntimeBenchmarkOnly

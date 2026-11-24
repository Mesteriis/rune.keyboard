package io.github.mesteriis.rune.runtime.llama

/** Separate manual opt-in from the exact-model qualification tests. */
@Target(AnnotationTarget.CLASS, AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
annotation class RuntimeBenchmarkOnly

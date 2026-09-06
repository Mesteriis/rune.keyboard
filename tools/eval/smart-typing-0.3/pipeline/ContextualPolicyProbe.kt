package io.github.mesteriis.rune.keyboard.smarttyping.punctuation

import java.io.File
import kotlin.system.exitProcess

/** Host-only numeric observer. All ranking arithmetic executes the actual production policy. */
object ContextualPolicyProbe {
    @JvmStatic fun main(args: Array<String>) {
        try {
            check(args.size == 1)
            var expected = 0
            File(args[0]).bufferedReader(Charsets.US_ASCII).useLines { lines ->
                lines.forEach { line ->
                    check(line.length <= 4096 && expected < 2048)
                    val fields = line.split('\t')
                    check(fields.size == 4 && fields[0].toInt() == expected)
                    check(fields[1] in setOf("ok", "error", "missing", "excluded"))
                    val chosen = if (fields[1] == "ok") choose(fields[2], fields[3]) else 0
                    println("$expected\t$chosen")
                    expected++
                }
            }
            check(expected > 0)
        } catch (_: Exception) {
            System.err.println("CONTEXTUAL_POLICY_PROBE_FAILED")
            exitProcess(1)
        }
    }

    private fun choose(ids: String, numeric: String): Int {
        val expectedIds = if (ids == "_") emptyList() else
            ids.split(',').map { it.toIntOrNull() ?: return 0 }
        val scores = if (numeric == "_") emptyList() else numeric.split(';').map { record ->
            val fields = record.split(',')
            if (fields.size != 3) return 0
            ContextualPunctuationPolicy.Score(fields[0].toIntOrNull() ?: return 0,
                fields[1].toDoubleOrNull() ?: return 0, fields[2].toIntOrNull() ?: return 0)
        }
        return ContextualPunctuationPolicy.choose(expectedIds, scores) ?: 0
    }
}

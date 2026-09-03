package io.github.mesteriis.rune.keyboard.smarttyping.punctuation

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.File
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.util.Base64
import kotlin.system.exitProcess

/** Host-only observer for the exact production contextual allowlist. */
object ContextualExport {
    @JvmStatic fun main(args: Array<String>) {
        try {
            check(args.size == 1)
            val decoder = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
            fun decoded(value: String) = decoder.decode(ByteBuffer.wrap(Base64.getDecoder().decode(value))).toString()
            fun encoded(value: String) = Base64.getEncoder().encodeToString(value.toByteArray(Charsets.UTF_8))
            File(args[0]).bufferedReader(Charsets.US_ASCII).useLines { lines ->
                var expected = 0
                lines.forEach { line ->
                    val fields = line.split('\t')
                    check(fields.size == 4 && fields[0].toInt() == expected && expected < 2000)
                    val language = KeyboardLanguage.entries.single { it.locale.language == fields[1] }
                    val variants = ContextualPunctuationEngine.variants(decoded(fields[2]), decoded(fields[3]), language)
                    check(variants.size in 2..8)
                    println("R\t$expected\t${variants.size}")
                    variants.forEach { variant ->
                        println(listOf("C", expected, variant.id, encoded(variant.boundary),
                            encoded(variant.continuation)).joinToString("\t"))
                    }
                    expected++
                }
            }
        } catch (_: Exception) {
            System.err.println("CONTEXTUAL_EXPORT_FAILED")
            exitProcess(1)
        }
    }
}

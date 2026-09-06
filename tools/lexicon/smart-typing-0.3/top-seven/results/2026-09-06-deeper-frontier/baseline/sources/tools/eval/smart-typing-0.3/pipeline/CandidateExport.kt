package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.File
import java.nio.channels.FileChannel
import java.nio.charset.CodingErrorAction
import java.nio.file.StandardOpenOption
import java.util.Base64
import kotlin.system.exitProcess

/** Offline public-corpus observer; the production generator receives no labels or expected words. */
object CandidateExport {
    @JvmStatic fun main(args: Array<String>) {
        try {
            check(args.size == 3 || args.size == 4)
            val maximumAlternatives = if (args.size == 4) args[3].toInt() else CandidateGenerator.MAX_ALTERNATIVES
            fun mapping(file: File) = FileChannel.open(file.toPath(), StandardOpenOption.READ).use {
                it.map(FileChannel.MapMode.READ_ONLY, 0, it.size())
            }
            val trusted = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN, FrozenPackedLexicons.SPANISH)
            val handles = trusted.map { trust ->
                val code = trust.language.locale.language
                val loaded = PackedLexiconData.validate(trust,
                    mapping(File(args[1], "$code.trie")), mapping(File(args[1], "$code.trie.lengths")),
                    mapping(File(args[2], "$code.ranks")))
                check(loaded is PackedLexiconLoad.Ready)
                loaded.lexicon
            }
            val generator = CandidateGenerator(PackedCandidateLexicon(handles), maximumAlternatives)
            val decoder = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
            File(args[0]).bufferedReader(Charsets.US_ASCII).useLines { lines ->
                var expected = 0
                lines.forEach { line ->
                    check(line.length <= 8192 && expected < 10000)
                    val fields = line.split('\t')
                    check(fields.size == 3 && fields[0].toInt() == expected)
                    val language = KeyboardLanguage.entries.single { it.locale.language == fields[1] }
                    val token = decoder.decode(java.nio.ByteBuffer.wrap(Base64.getDecoder().decode(fields[2]))).toString()
                    val result = generator.generate(token, language)
                    check(result.original == token)
                    println(listOf("R", expected, result.completion.name, result.isValidWord,
                        result.prohibitsAutoReplace, result.inspectedStates, result.verifiedTerminals,
                        result.protectedReason?.name ?: "NONE", result.alternatives.size).joinToString("\t"))
                    result.alternatives.forEachIndexed { index, c ->
                        fun encoded(s: String) = Base64.getEncoder().encodeToString(s.toByteArray(Charsets.UTF_8))
                        println(listOf("C", expected, index + 1, encoded(c.text), encoded(c.canonicalKey),
                            encoded(c.terminalKey), c.language.locale.language, c.isFallback, c.languagePrior,
                            c.frequencyRank, c.unitDistance, c.editFeatures.editCost,
                            c.editFeatures.repeatedCharacterEdits, c.editFeatures.repetitionBonus,
                            c.lengthDifference, c.casePattern.name).joinToString("\t"))
                    }
                    expected++
                }
            }
        } catch (_: Exception) {
            System.err.println("CANDIDATE_EXPORT_FAILED")
            exitProcess(1)
        }
    }
}

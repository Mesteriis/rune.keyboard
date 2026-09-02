package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.File
import java.nio.channels.FileChannel
import java.nio.file.StandardOpenOption
import kotlin.system.exitProcess

private data class OracleWord(val ordinal: Int, val display: String, val key: String)
private fun decode(text: String): String = if (text == "-") "" else String(text.split(',').map { it.toInt(16).toChar() }.toCharArray())
private fun row(vararg values: Int) { println(values.joinToString("\t")) }

/** Observer only: no state charging, pruning, ranking or query rewriting. */
private class Trace(private val delegate: CandidateLexicon) : CandidateLexicon {
    var request = 0
    var words = emptyMap<Pair<Int, String>, OracleWord>()
    val records = mutableListOf<IntArray>()
    private var visits = 0
    fun begin(id: Int, expected: Map<Pair<Int, String>, OracleWord>) {
        request = id; words = expected; records.clear(); visits = 0
    }
    override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
        val before = control.inspectedStates
        val result = delegate.exact(language, key, control)
        records.add(intArrayOf(1, 3, request, language.ordinal, result.ordinal, control.inspectedStates - before))
        return result
    }
    override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int, control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus {
        val beforeStates = control.inspectedStates
        val beforeVerified = control.verifiedTerminals
        val result = delegate.scan(language, key, unitRadius, control) { terminal, rank ->
            val before = control.verifiedTerminals
            val keep = visitor.visit(terminal, rank)
            records.add(intArrayOf(1, 5, request, visits++, language.ordinal,
                words[language.ordinal to terminal]?.ordinal ?: -1, rank,
                control.verifiedTerminals - before, if (keep) 1 else 0))
            keep
        }
        records.add(intArrayOf(1, 4, request, language.ordinal, result.ordinal,
            control.inspectedStates - beforeStates, control.verifiedTerminals - beforeVerified))
        return result
    }
    fun finish() { records.clear(); words = emptyMap() }
}

object QualificationMain {
    @JvmStatic fun main(args: Array<String>) {
        try {
            check(args.size == 3)
            val fixture = File(args[0]); val assets = File(args[1]); val ranks = File(args[2])
            val trusted = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN, FrozenPackedLexicons.SPANISH)
            fun mapping(file: File) = FileChannel.open(file.toPath(), StandardOpenOption.READ).use {
                it.map(FileChannel.MapMode.READ_ONLY, 0, it.size())
            }
            val handles = trusted.map { trust ->
                val language = when (trust.language) {
                    KeyboardLanguage.ENGLISH -> "en"
                    KeyboardLanguage.RUSSIAN -> "ru"
                    KeyboardLanguage.SPANISH -> "es"
                }
                val result = PackedLexiconData.validate(trust, mapping(File(assets, "$language.trie")),
                    mapping(File(assets, "$language.trie.lengths")), mapping(File(ranks, "$language.ranks")))
                when (result) {
                    is PackedLexiconLoad.Ready -> { row(1, 0, trust.language.ordinal, result.lexicon.wordCount, result.lexicon.nodeCount); result.lexicon }
                    is PackedLexiconLoad.Failed -> { row(1, 9, trust.language.ordinal, result.reason.ordinal); exitProcess(2) }
                }
            }
            val lookup = mutableMapOf<Int, MutableMap<Pair<Int, String>, OracleWord>>()
            File(fixture, "candidates.tsv").forEachLine { line ->
                if (line.isNotEmpty()) {
                    val cells = line.split('\t'); check(cells.size == 15)
                    val id = cells[0].toInt(); val language = cells[1].toInt()
                    lookup.getOrPut(id) { mutableMapOf() }[language to decode(cells[3])] =
                        OracleWord(cells[2].toInt(), decode(cells[4]), decode(cells[5]))
                }
            }
            val trace = Trace(PackedCandidateLexicon(handles))
            val generator = CandidateGenerator(trace)
            var count = 0
            File(fixture, "inputs.tsv").forEachLine { line ->
                val fields = line.split('\t'); check(fields.size == 5)
                val id = fields[0].toInt(); val token = decode(fields[4]); val cancel = fields[3] == "1"
                trace.begin(id, lookup[id] ?: emptyMap())
                try {
                    val result = generator.generate(token, KeyboardLanguage.entries[fields[2].toInt()], CandidateCancellation { cancel })
                    row(1, 1, id, fields[1].toInt(), fields[2].toInt(), result.completion.ordinal,
                        if (result.isValidWord) 1 else 0, if (result.prohibitsAutoReplace) 1 else 0,
                        if (if (cancel) result.original == null else result.original == token) 1 else 0,
                        result.inspectedStates, result.verifiedTerminals, result.protectedReason?.ordinal ?: -1,
                        result.alternatives.size)
                    result.alternatives.forEachIndexed { position, candidate ->
                        val oracle = trace.words[candidate.language.ordinal to candidate.terminalKey]
                        row(1, 2, id, position, candidate.language.ordinal, oracle?.ordinal ?: -1,
                            if (candidate.isFallback) 1 else 0, candidate.languagePrior, candidate.frequencyRank,
                            candidate.unitDistance, (candidate.editFeatures.editCost * 4).toInt(),
                            candidate.editFeatures.repeatedCharacterEdits, (candidate.editFeatures.repetitionBonus * 4).toInt(),
                            candidate.lengthDifference, candidate.casePattern.ordinal,
                            if (candidate.text == oracle?.display) 1 else 0,
                            if (candidate.canonicalKey == oracle?.key) 1 else 0)
                    }
                    for (record in trace.records) row(*record)
                    count++
                } finally { trace.finish() }
            }
            row(1, 6, count)
        } catch (_: Throwable) { row(1, 9, 99); exitProcess(2) }
    }
}

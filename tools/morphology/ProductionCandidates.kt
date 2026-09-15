package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedSpellingPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.LocalCorrectionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CommonConfusions
import java.io.File
import java.nio.channels.FileChannel
import java.nio.file.StandardOpenOption
import java.security.MessageDigest
import java.util.Base64

/** Host-only candidate observer. Receives no expected spelling, context or labels. */
object ProductionCandidates {
    private fun json(value: Any?): String = when (value) {
        null -> "null"
        is String -> buildString {
            append('"')
            value.forEach { c -> when (c) {
                '"' -> append("\\\""); '\\' -> append("\\\\")
                else -> if (c.code < 32 || c.isSurrogate()) append("\\u%04x".format(c.code)) else append(c)
            } }
            append('"')
        }
        is Boolean, is Number -> value.toString()
        is Map<*, *> -> value.entries.joinToString(",", "{", "}") { json(it.key.toString()) + ":" + json(it.value) }
        is Iterable<*> -> value.joinToString(",", "[", "]") { json(it) }
        else -> error("JSON_TYPE")
    }

    private fun candidate(c: GeneratedCandidate) = mapOf(
        "text" to c.text, "canonicalKey" to c.canonicalKey, "terminalKey" to c.terminalKey,
        "language" to c.language.locale.language, "isFallback" to c.isFallback,
        "frequencyRank" to c.frequencyRank, "unitDistance" to c.unitDistance,
        "editCost" to c.editFeatures.editCost, "casePattern" to c.casePattern.name,
        "kind" to c.kind.name)

    private fun generation(g: CandidateGeneration) = mapOf(
        "original" to g.original, "completion" to g.completion.name, "isValidWord" to g.isValidWord,
        "protectedReason" to g.protectedReason?.name, "prohibitsAutoReplace" to g.prohibitsAutoReplace,
        "inspectedStates" to g.inspectedStates, "verifiedTerminals" to g.verifiedTerminals,
        "alternatives" to g.alternatives.map(::candidate),
        "localSearch" to mapOf("completion" to g.localSearch.completion.name,
            "inspectedStates" to g.localSearch.inspectedStates,
            "verifiedTerminals" to g.localSearch.verifiedTerminals,
            "alternatives" to g.localSearch.alternatives.map(::candidate)))

    @JvmStatic fun main(args: Array<String>) {
        check(args.size == 2)
        val assets = File(args[1])
        fun mapping(file: File) = FileChannel.open(file.toPath(), StandardOpenOption.READ).use {
            it.map(FileChannel.MapMode.READ_ONLY, 0, it.size())
        }
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN,
            FrozenPackedLexicons.SPANISH).map { trust ->
            val language = trust.language.locale.language
            val load = PackedLexiconData.validate(trust,
                mapping(File(assets, "smarttyping/lexicon/$language.trie")),
                mapping(File(assets, "smarttyping/lexicon/$language.trie.lengths")),
                mapping(File(assets, "smarttyping/lexicon/frequency/$language.ranks")))
            check(load is PackedLexiconLoad.Ready) { "PACKED_ASSET_NOT_READY" }; load.lexicon
        }
        val cases = KeyboardLanguage.entries.associateWith { language ->
            val trust = FrozenCanonicalCaseLexicons.forLanguage(language)
            val bytes = File(assets, trust.path).readBytes()
            val digest = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
            check(bytes.size.toLong() == trust.bytes && digest == trust.sha256) { "CASE_HASH" }
            CanonicalCaseData.validate(bytes)
        }
        val generator = CandidateGenerator(PackedCandidateLexicon(handles), CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES,
            CanonicalCaseLexicon { language, key -> cases.getValue(language).lookup(key) })
        File(args[0]).useLines { lines -> lines.forEachIndexed { index, line ->
            val fields = line.split('\t')
            check(fields.size == 2 && fields[0].toInt() == index) { "INPUT_ENVELOPE" }
            val token = String(Base64.getDecoder().decode(fields[1]), Charsets.UTF_8)
            val started = System.nanoTime()
            val g = generator.generate(token, KeyboardLanguage.RUSSIAN)
            val elapsed = (System.nanoTime() - started) / 1_000_000.0
            val baselineStart = System.nanoTime()
            val common = CommonConfusions.preferredId(g, KeyboardLanguage.RUSSIAN)
            val baseline = if (common > 0) g.alternatives[common - 1].canonicalKey else
                LocalCorrectionPolicy.decide(g, KeyboardLanguage.RUSSIAN)?.canonicalKey
            val baselineMs = (System.nanoTime() - baselineStart) / 1_000_000.0
            println(json(mapOf("index" to index, "generation" to generation(g), "baseline" to baseline,
                "generationMs" to elapsed, "baselineMs" to baselineMs)))
        } }
    }
}

package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.nio.channels.FileChannel
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardOpenOption
import org.junit.Assert.*
import org.junit.Test

class CommonConfusionsTest {
    private val examples = listOf(
        Triple(KeyboardLanguage.RUSSIAN, "автокрекция", "автокоррекция"),
        Triple(KeyboardLanguage.RUSSIAN, "арфография", "орфография"),
        Triple(KeyboardLanguage.RUSSIAN, "сообшение", "сообщение"),
        Triple(KeyboardLanguage.RUSSIAN, "реалбно", "реально"),
        Triple(KeyboardLanguage.RUSSIAN, "мододец", "молодец"),
        Triple(KeyboardLanguage.RUSSIAN, "шоржусь", "горжусь"),
        Triple(KeyboardLanguage.ENGLISH, "teh", "the"),
        Triple(KeyboardLanguage.ENGLISH, "recieve", "receive"),
        Triple(KeyboardLanguage.ENGLISH, "adress", "address"),
        Triple(KeyboardLanguage.SPANISH, "mensage", "mensaje"),
        Triple(KeyboardLanguage.SPANISH, "correcion", "corrección"),
    )

    @Test fun `every named mapping is a packaged lexicon member published alongside exact original`() {
        val root = listOf(Path.of("src/main/assets"), Path.of("app/src/main/assets")).first { Files.isDirectory(it) }
        fun mapping(path: String) = FileChannel.open(root.resolve(path), StandardOpenOption.READ).use {
            it.map(FileChannel.MapMode.READ_ONLY, 0, it.size())
        }
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN,
            FrozenPackedLexicons.SPANISH).map { trust ->
            val lang = trust.language.locale.language
            val load = PackedLexiconData.validate(trust, mapping("smarttyping/lexicon/$lang.trie"),
                mapping("smarttyping/lexicon/$lang.trie.lengths"), mapping("smarttyping/lexicon/frequency/$lang.ranks"))
            assertTrue(load is PackedLexiconLoad.Ready)
            (load as PackedLexiconLoad.Ready).lexicon
        }
        val lexicon = PackedCandidateLexicon(handles)
        val generator = CandidateGenerator(lexicon)
        for ((language, original, target) in examples) {
            assertEquals(target, ExactMembership.PRESENT, lexicon.exact(language, target, CandidateSearchControl { false }))
            val result = generator.generate(original, language)
            assertEquals(original, result.original)
            assertEquals(original, CandidateCompletion.COMPLETE, result.completion)
            assertTrue("$original -> $target: ${result.completion}", result.alternatives.any {
                it.text == target && it.kind == GeneratedCandidateKind.COMMON_CONFUSION
            })
        }
    }

    @Test fun `unvalidated target and protected input never publish a mapped candidate`() {
        for (membership in listOf(ExactMembership.ABSENT, ExactMembership.UNAVAILABLE)) {
            val generator = CandidateGenerator(object : CandidateLexicon {
                override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl) =
                    if (key == "the") membership else ExactMembership.ABSENT
                override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                    control: CandidateSearchControl, visitor: CandidateVisitor) = LexiconScanStatus.COMPLETE
            })
            for (token in listOf("teh", "TEH", "@teh", "teh/", "teH")) {
                val result = generator.generate(token, KeyboardLanguage.ENGLISH)
                assertTrue(result.alternatives.isEmpty())
            }
        }
    }

    @Test fun `verified mapping completes its bounded retrieval without extended search`() {
        var scans = 0
        val generator = CandidateGenerator(object : CandidateLexicon {
            override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl) =
                if (key == "the") ExactMembership.PRESENT else ExactMembership.ABSENT
            override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus {
                scans++
                repeat(CandidateSearchControl.MAX_STATES + 1) { control.inspectState() }
                return LexiconScanStatus.UNAVAILABLE
            }
        })
        val result = generator.generate("teh", KeyboardLanguage.ENGLISH)
        assertEquals(CandidateCompletion.COMPLETE, result.completion)
        assertEquals(listOf("the"), result.alternatives.map { it.text })
        assertEquals(0, scans)
    }

    @Test fun `unverified mapping falls back to extended search and retains its incomplete veto`() {
        var scans = 0
        val generator = CandidateGenerator(object : CandidateLexicon {
            override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl) = ExactMembership.ABSENT
            override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus {
                scans++
                repeat(CandidateSearchControl.MAX_STATES + 1) { control.inspectState() }
                return LexiconScanStatus.UNAVAILABLE
            }
        })
        val result = generator.generate("teh", KeyboardLanguage.ENGLISH)
        assertEquals(1, scans)
        assertEquals(CandidateCompletion.STATES_EXHAUSTED, result.completion)
        assertTrue(result.prohibitsAutoReplace)
        assertTrue(result.alternatives.isEmpty())
    }

    @Test fun `target verification failure cancellation or exhaustion never publishes mapping`() {
        for (completion in listOf(CandidateCompletion.READER_FAILURE, CandidateCompletion.UNAVAILABLE,
            CandidateCompletion.CANCELLED, CandidateCompletion.STATES_EXHAUSTED, CandidateCompletion.VERIFIED_EXHAUSTED)) {
            var cancelled = false
            val generator = CandidateGenerator(object : CandidateLexicon {
                override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
                    when (completion) {
                        CandidateCompletion.READER_FAILURE -> error("reader failure")
                        CandidateCompletion.CANCELLED -> cancelled = true
                        CandidateCompletion.STATES_EXHAUSTED -> repeat(CandidateSearchControl.MAX_STATES + 1) { control.inspectState() }
                        CandidateCompletion.VERIFIED_EXHAUSTED -> repeat(CandidateSearchControl.MAX_VERIFIED + 1) { control.verifyTerminal() }
                        else -> Unit
                    }
                    return ExactMembership.UNAVAILABLE
                }
                override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                    control: CandidateSearchControl, visitor: CandidateVisitor) = LexiconScanStatus.UNAVAILABLE
            })
            val result = generator.generate("teh", KeyboardLanguage.ENGLISH, CandidateCancellation { cancelled })
            assertEquals(completion, result.completion)
            assertTrue(result.prohibitsAutoReplace)
            assertTrue(result.alternatives.isEmpty())
        }
    }
}

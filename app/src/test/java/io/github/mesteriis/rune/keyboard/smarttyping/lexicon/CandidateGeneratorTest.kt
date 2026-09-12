package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditCostProfile
import io.github.mesteriis.rune.keyboard.smarttyping.correction.WeightedDamerauLevenshtein
import java.io.IOException
import org.junit.Assert.*
import org.junit.Test

class CandidateGeneratorTest {
    private val en = KeyboardLanguage.ENGLISH
    private val es = KeyboardLanguage.SPANISH
    private val ru = KeyboardLanguage.RUSSIAN

    @Test
    fun `protected input never calls a lexicon and keeps the exact original`() {
        val lexicon = ScriptedLexicon(emptyMap())
        val generator = CandidateGenerator(lexicon)
        for (token in listOf("", "HTTP", "getValue", "foo_bar", "x/y", "a@b", "v2", "аb", "a".repeat(33), "\uD800")) {
            val result = generator.generate(token, en)
            assertEquals(token, result.original)
            assertEquals(CandidateCompletion.PROTECTED, result.completion)
            assertNotNull(result.protectedReason)
            assertTrue(result.prohibitsAutoReplace)
            assertTrue(result.alternatives.isEmpty())
        }
        assertEquals(0, lexicon.exactCalls)
        assertTrue(lexicon.scanned.isEmpty())
    }

    @Test
    fun `valid primary or fallback words are original only even when another valid word is nearby`() {
        for ((token, language, entries) in listOf(
            Triple("form", en, mapOf(en to listOf(Entry("form"), Entry("from")))),
            Triple("esta", en, mapOf(es to listOf(Entry("esta"), Entry("está")))),
            Triple("все", ru, mapOf(ru to listOf(Entry("все"), Entry("всё")))),
        )) {
            val lexicon = ScriptedLexicon(entries)
            val result = CandidateGenerator(lexicon).generate(token, language)
            assertEquals(CandidateCompletion.VALID_WORD, result.completion)
            assertTrue(result.isValidWord)
            assertTrue(result.prohibitsAutoReplace)
            assertEquals(token, result.original)
            assertTrue(result.alternatives.isEmpty())
            assertTrue(lexicon.scanned.isEmpty())
        }
    }

    @Test
    fun `lowercase valid proper noun exposes canonical title case without automatic eligibility`() {
        val lexicon = ScriptedLexicon(mapOf(
            ru to listOf(Entry("москва")),
            en to listOf(Entry("london")),
            es to listOf(Entry("juan")),
        ))
        val canonical = CanonicalCaseLexicon { language, key -> when (language to key) {
            ru to "москва" -> CanonicalCase("Москва", true)
            en to "london" -> CanonicalCase("London", true)
            es to "juan" -> CanonicalCase("Juan", false)
            else -> null
        } }
        for ((token, language, expected) in listOf(
            Triple("москва", ru, "Москва"),
            Triple("london", en, "London"),
            Triple("juan", es, "Juan"),
        )) {
            val result = CandidateGenerator(lexicon, canonicalCaseLexicon = canonical)
                .generate(token, language)
            assertEquals(CandidateCompletion.VALID_WORD, result.completion)
            assertTrue(result.isValidWord)
            assertTrue(result.prohibitsAutoReplace)
            assertEquals(listOf(expected), result.alternatives.map { it.text })
            assertEquals(GeneratedCandidateKind.CANONICAL_CASE, result.alternatives.single().kind)
            assertEquals(token != "juan", result.alternatives.single().canonicalCaseUnambiguous)
            assertEquals(token != "juan", result.alternatives.single().canonicalCaseAutoEligible)
        }
        assertTrue(CandidateGenerator(lexicon, canonicalCaseLexicon = canonical)
            .generate("London", en).alternatives.isEmpty())
    }

    @Test
    fun `canonical auto eligibility requires agreement from every present routed language`() {
        val lexicon = ScriptedLexicon(mapOf(en to listOf(Entry("si")), es to listOf(Entry("si"))))
        for (competing in listOf(null, CanonicalCase("Si", false), CanonicalCase("Sí", true), CanonicalCase("Si", true))) {
            val cases = CanonicalCaseLexicon { language, _ -> if (language == en) CanonicalCase("Si", true) else competing }
            val result = CandidateGenerator(lexicon, canonicalCaseLexicon = cases).generate("si", en)
            val candidate = result.alternatives.single()
            assertEquals(CandidateCompletion.VALID_WORD, result.completion)
            assertEquals("Si", candidate.text)
            assertTrue(candidate.canonicalCaseUnambiguous)
            assertEquals(competing == CanonicalCase("Si", true), candidate.canonicalCaseAutoEligible)
        }
    }

    @Test
    fun `unknown cancelled or exhausted competing membership never enables canonical auto`() {
        for (mode in 0..3) {
            var cancelled = false
            val lexicon = object : CandidateLexicon {
                override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
                    if (language == en) return ExactMembership.PRESENT
                    when (mode) {
                        1 -> cancelled = true
                        2 -> repeat(CandidateSearchControl.MAX_STATES + 1) { control.inspectState() }
                        3 -> throw IOException("synthetic reader failure")
                    }
                    return ExactMembership.UNAVAILABLE
                }
                override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                    control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus =
                    error("Exact canonical path must not scan")
            }
            val cases = CanonicalCaseLexicon { _, _ -> CanonicalCase("London", true) }
            val result = CandidateGenerator(lexicon, canonicalCaseLexicon = cases)
                .generate("london", en, CandidateCancellation { cancelled })
            assertFalse(result.alternatives.any { it.canonicalCaseAutoEligible })
            assertEquals(listOf(CandidateCompletion.VALID_WORD, CandidateCompletion.CANCELLED,
                CandidateCompletion.STATES_EXHAUSTED, CandidateCompletion.READER_FAILURE)[mode], result.completion)
            if (mode == 1) assertNull(result.original)
            assertTrue(result.inspectedStates <= CandidateSearchControl.MAX_STATES)
        }
    }

    @Test
    fun `script and Spanish accents route before layout and preserve canonical accents and title case`() {
        val lexicon = ScriptedLexicon(mapOf(
            ru to listOf(Entry("ёжик")), es to listOf(Entry("niño"), Entry("café")),
        ))
        val generator = CandidateGenerator(lexicon)
        val russian = generator.generate("Ёжк", en)
        assertEquals(listOf("Ёжик"), russian.alternatives.map { it.text })
        assertEquals(listOf(ru), lexicon.scanned.toList())
        lexicon.scanned.clear()
        val spanish = generator.generate("Nin\u0303", ru)
        assertEquals(listOf("Niño"), spanish.alternatives.map { it.text })
        assertEquals(listOf(es), lexicon.scanned.toList())
        val decomposed = generator.generate("cafe\u0301", en)
        assertEquals(CandidateCompletion.VALID_WORD, decomposed.completion)
        assertEquals("cafe\u0301", decomposed.original)
    }

    @Test
    fun `unit admission is independent of weighted cost and changes radius at five scalars`() {
        val short = CandidateGenerator(ScriptedLexicon(mapOf(en to listOf(Entry("ba"), Entry("ss")))))
            .generate("ab", en)
        assertEquals(listOf("ba"), short.alternatives.map { it.text })
        assertEquals(1, short.alternatives.single().unitDistance)
        assertEquals(1.25, short.alternatives.single().editFeatures.editCost, 0.0)
        val long = CandidateGenerator(ScriptedLexicon(mapOf(en to listOf(Entry("abccca")))))
            .generate("cacca", en)
        // CA -> ABC plus unchanged suffix needs two unrestricted edits (OSA would need three).
        assertEquals(listOf("abccca"), long.alternatives.map { it.text })
        assertEquals(2, long.alternatives.single().unitDistance)
        val four = CandidateGenerator(ScriptedLexicon(mapOf(en to listOf(Entry("ssaa")))))
            .generate("aaaa", en)
        assertTrue(four.alternatives.isEmpty())
    }

    @Test
    fun `observed short manual correction stays available for model ranking`() {
        val result = CandidateGenerator(ScriptedLexicon(mapOf(ru to listOf(Entry("муж", 20)))))
            .generate("мкж", ru)

        assertEquals(CandidateCompletion.UNAVAILABLE, result.localSearch.completion)
        assertEquals(listOf("муж"), result.alternatives.map { it.text })
        assertTrue(result.localSearch.alternatives.isEmpty())
        assertFalse(result.isValidWord)
    }

    @Test
    fun `complete distance one evidence survives an exhausted extended search`() {
        var scans = 0
        val lexicon = object : CandidateLexicon {
            override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl) =
                if (control.inspectState()) ExactMembership.ABSENT else ExactMembership.UNAVAILABLE

            override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus {
                scans++
                if (unitRadius == 1) {
                    if (!control.inspectState() || !visitor.visit("result", 1)) return LexiconScanStatus.UNAVAILABLE
                    return LexiconScanStatus.COMPLETE
                }
                while (control.inspectState()) Unit
                return LexiconScanStatus.UNAVAILABLE
            }
        }

        val result = CandidateGenerator(lexicon).generate("resul", en)

        assertEquals(CandidateCompletion.STATES_EXHAUSTED, result.completion)
        assertEquals(CandidateCompletion.COMPLETE, result.localSearch.completion)
        assertEquals(listOf("result"), result.localSearch.alternatives.map { it.text })
        assertTrue(scans >= 2)
    }

    @Test
    fun `late weighted winner is evaluated even after seven unit neighbors`() {
        val words = listOf("baxxx", "acxxx", "abxyx", "abxxy", "abxzx", "abxxz", "abxxxq", "apxxx")
        val lexicon = ScriptedLexicon(mapOf(en to words.mapIndexed { index, word -> Entry(word, index + 1) }))
        val result = CandidateGenerator(lexicon).generate("abxxx", en)
        assertEquals(CandidateCompletion.COMPLETE, result.completion)
        assertEquals(16, result.verifiedTerminals)
        assertEquals(7, result.alternatives.size)
        assertTrue(result.alternatives.any { it.text == "apxxx" })
        assertFalse(result.alternatives.any { it.text == "baxxx" })
        assertTrue(result.alternatives.first().editFeatures.editCost <= 1.0)
    }

    @Test
    fun `dedup and fallback quota apply after full ranking and keep filling seven unique slots`() {
        val primary = listOf("bcat", "ccat", "dcat", "ecat", "fcat", "gcat", "hcat").map { Entry(it, 100) }
        val fallback = listOf("bcat", "ccat", "icat", "jcat", "kcat").map { Entry(it, 1) }
        val result = CandidateGenerator(ScriptedLexicon(mapOf(en to primary, es to fallback)))
            .generate("cat", en)
        assertEquals(7, result.alternatives.size)
        assertEquals(12, result.verifiedTerminals)
        assertEquals(7, result.alternatives.map { it.canonicalKey }.toSet().size)
        assertEquals(0, result.alternatives.count { it.isFallback }) // Equal costs: primary prior wins.
        val reverse = CandidateGenerator(ScriptedLexicon(mapOf(es to primary, en to fallback)))
            .generate("cat", es)
        assertEquals(result.alternatives.map { it.text }, reverse.alternatives.map { it.text })
        assertTrue(reverse.alternatives.all { it.language == es })
    }

    @Test
    fun `cheaper fallback wins before prior but only two fallback representations survive`() {
        val lexicon = ScriptedLexicon(mapOf(
            en to listOf("p", "o", "i", "u", "j", "k", "l").map { Entry(it) },
            es to listOf("q", "w", "s", "z").map { Entry(it) },
        ))
        val result = CandidateGenerator(lexicon).generate("a", en)
        assertEquals(7, result.alternatives.size)
        assertEquals(2, result.alternatives.count { it.isFallback })
        assertTrue(result.alternatives.take(2).all { it.isFallback })
        assertTrue(result.alternatives.take(2).all { it.editFeatures.editCost == 0.75 })
    }

    @Test
    fun `unrepresentable title expansion cannot consume one of seven alternatives`() {
        val tail = "a".repeat(31)
        val entries = listOf(Entry("ß" + tail, 1)) + ('b'..'i').map { Entry(it + tail, 100) }
        val result = CandidateGenerator(ScriptedLexicon(mapOf(en to entries))).generate("A" + tail, en)
        assertEquals(CandidateCompletion.COMPLETE, result.completion)
        assertEquals(18, result.verifiedTerminals)
        assertEquals(7, result.alternatives.size)
        assertTrue(result.alternatives.all { it.text.codePointCount(0, it.text.length) == 32 })
        assertTrue(result.alternatives.all { it.text.first().isUpperCase() })
        assertFalse(result.alternatives.any { it.text.startsWith("Ss") })
    }

    @Test
    fun `case expansion display collisions deduplicate before final selection`() {
        val result = CandidateGenerator(ScriptedLexicon(mapOf(en to listOf(Entry("ßx", 1), Entry("ssx", 2)))))
            .generate("Sx", en)
        assertEquals(CandidateCompletion.COMPLETE, result.completion)
        assertEquals(2, result.verifiedTerminals)
        assertEquals(listOf("Ssx"), result.alternatives.map { it.text })
        assertEquals(1, result.alternatives.single().frequencyRank)
    }

    @Test
    fun `equal ranked display collisions retain identical full feature snapshots in either order`() {
        val entries = listOf(Entry("ßx"), Entry("ssx"))
        val forward = CandidateGenerator(ScriptedLexicon(mapOf(en to entries))).generate("Sx", en)
        val reversed = CandidateGenerator(ScriptedLexicon(mapOf(en to entries.reversed()))).generate("Sx", en)
        assertEquals(CandidateCompletion.COMPLETE, forward.completion)
        assertEquals(forward, reversed)
        val candidate = forward.alternatives.single()
        assertEquals("Ssx", candidate.text)
        assertEquals("ssx", candidate.terminalKey)
        assertEquals(1, candidate.editFeatures.repeatedCharacterEdits)
        assertEquals(0.25, candidate.editFeatures.repetitionBonus, 0.0)
        assertEquals(1, candidate.lengthDifference)
    }

    @Test
    fun `unit and repetition features are retained without negative cost discounts`() {
        val result = CandidateGenerator(ScriptedLexicon(mapOf(en to listOf(Entry("hello", 25)))))
            .generate("helllo", en)
        val candidate = result.alternatives.single()
        assertEquals(1, candidate.unitDistance)
        assertEquals(1.0, candidate.editFeatures.editCost, 0.0)
        assertEquals(1, candidate.editFeatures.repeatedCharacterEdits)
        assertEquals(0.25, candidate.editFeatures.repetitionBonus, 0.0)
        assertEquals(25, candidate.frequencyRank)
        assertEquals(1, candidate.lengthDifference)
        assertEquals(4, candidate.languagePrior)
    }

    @Test
    fun `states are shared by both exact lookups and both scans with exact limit completion`() {
        val lexicon = ScriptedLexicon(mapOf(en to listOf(Entry("cat")), es to listOf(Entry("cot"))))
        // Two exact reads + one primary terminal + 8188 fallback prefix states + one terminal.
        lexicon.scanPrefixStates[es] = 8_188
        val generator = CandidateGenerator(lexicon)
        val complete = generator.generate("cut", en)
        assertEquals(CandidateCompletion.COMPLETE, complete.completion)
        assertEquals(CandidateCompletion.UNAVAILABLE, complete.localSearch.completion)
        assertEquals(8_192, complete.inspectedStates)
        assertEquals(2, complete.verifiedTerminals)
        lexicon.scanPrefixStates[es] = 8_189
        val exhausted = generator.generate("cut", en)
        assertEquals(CandidateCompletion.STATES_EXHAUSTED, exhausted.completion)
        assertEquals(8_192, exhausted.inspectedStates)
        assertEquals(1, exhausted.verifiedTerminals)
        assertFalse(exhausted.isComplete)
        assertTrue(exhausted.prohibitsAutoReplace)
        assertEquals(listOf("cat"), exhausted.alternatives.map { it.text })
    }

    @Test
    fun `exact lookup exhaustion cannot be mistaken for an absent original`() {
        val lexicon = ScriptedLexicon(mapOf(es to listOf(Entry("form"))))
        lexicon.exactStates[en] = 8_192
        val result = CandidateGenerator(lexicon).generate("form", en)
        assertEquals(CandidateCompletion.STATES_EXHAUSTED, result.completion)
        assertEquals(8_192, result.inspectedStates)
        assertFalse(result.isValidWord)
        assertTrue(result.prohibitsAutoReplace)
        assertTrue(lexicon.scanned.isEmpty())
    }

    @Test
    fun `verified cap is shared and charges losers and duplicates before topN`() {
        val words = neighborWords()
        val primary = words.take(40).map { Entry(it) }
        val lexicon = ScriptedLexicon(mapOf(en to primary, es to words.take(24).map { Entry(it) }))
        val complete = CandidateGenerator(lexicon).generate("aaaaa", en)
        assertEquals(CandidateCompletion.VERIFIED_EXHAUSTED, complete.completion)
        assertEquals(CandidateCompletion.COMPLETE, complete.localSearch.completion)
        assertEquals(64, complete.verifiedTerminals)
        assertEquals(7, complete.alternatives.size)
        val overflow = ScriptedLexicon(mapOf(en to primary, es to words.take(25).map { Entry(it) }))
        val result = CandidateGenerator(overflow).generate("aaaaa", en)
        assertEquals(CandidateCompletion.VERIFIED_EXHAUSTED, result.completion)
        assertEquals(CandidateCompletion.VERIFIED_EXHAUSTED, result.localSearch.completion)
        assertEquals(64, result.verifiedTerminals)
        assertEquals(complete.alternatives, result.alternatives)
        assertFalse(result.isComplete)
        assertTrue(result.prohibitsAutoReplace)
    }

    @Test
    fun `both exhausted statuses preserve dedup quota and best verified seven with no automatic eligibility`() {
        val (primary, fallback) = partialDictionaries()
        // Complete enumeration of only the first 64 verified entries supplies a bounded control.
        val verifiedPrefix = ScriptedLexicon(mapOf(en to primary, es to fallback.take(14)))
        val expected = CandidateGenerator(verifiedPrefix).generate("aaaaa", en)
        assertEquals(CandidateCompletion.VERIFIED_EXHAUSTED, expected.completion)
        assertEquals(CandidateCompletion.COMPLETE, expected.localSearch.completion)
        assertEquals(64, expected.verifiedTerminals)
        assertEquals(7, expected.alternatives.size)
        assertEquals(2, expected.alternatives.count { it.isFallback })
        for (stateCap in listOf(true, false)) {
            val lexicon = ScriptedLexicon(mapOf(en to primary, es to fallback))
            if (stateCap) lexicon.scanPrefixStates[es] = 8_126
            val generator = CandidateGenerator(lexicon)
            val partial = generator.generate("aaaaa", en)
            assertEquals(if (stateCap) CandidateCompletion.STATES_EXHAUSTED else CandidateCompletion.VERIFIED_EXHAUSTED,
                partial.completion)
            assertEquals(64, partial.verifiedTerminals)
            assertEquals(if (stateCap) 8_192 else 67, partial.inspectedStates)
            assertEquals(7, partial.alternatives.map { it.canonicalKey }.toSet().size)
            assertEquals(2, partial.alternatives.count { it.isFallback })
            assertEquals(if (stateCap) CandidateCompletion.STATES_EXHAUSTED else CandidateCompletion.VERIFIED_EXHAUSTED,
                partial.localSearch.completion)
            assertFalse(partial.isComplete)
            assertTrue(partial.prohibitsAutoReplace)
            assertScratchCleared(generator)
        }
    }

    @Test
    fun `late cancellation during partial selection discards verified alternatives after either cap`() {
        for (stateCap in listOf(true, false)) {
            val (primary, fallback) = partialDictionaries()
            val lexicon = ScriptedLexicon(mapOf(en to primary, es to fallback))
            if (stateCap) lexicon.scanPrefixStates[es] = 8_126
            var checksAfterStop = 0
            var exhausted = false
            lexicon.afterStop = { exhausted = true }
            val generator = CandidateGenerator(lexicon)
            val result = generator.generate("aaaaa", en) {
                // Let scan-exit and selection-entry checkpoints pass; cancel within selection.
                exhausted && ++checksAfterStop == 3
            }
            assertTrue(exhausted)
            assertEquals(3, checksAfterStop)
            assertEquals(CandidateCompletion.CANCELLED, result.completion)
            assertEquals(64, result.verifiedTerminals)
            assertNull(result.original)
            assertTrue(result.alternatives.isEmpty())
            assertFalse(result.isComplete)
            assertTrue(result.prohibitsAutoReplace)
            assertScratchCleared(generator)
        }
    }

    @Test
    fun `checked reader exception after exhaustion discards partials and respects cancellation`() {
        for (stateCap in listOf(true, false)) for (cancel in listOf(true, false)) {
            val (primary, fallback) = partialDictionaries()
            val lexicon = ScriptedLexicon(mapOf(en to primary, es to fallback))
            if (stateCap) lexicon.scanPrefixStates[es] = 8_126
            var cancelled = false
            lexicon.afterStop = {
                cancelled = cancel
                throw IOException("CHECKED_CAP_SENTINEL")
            }
            val generator = CandidateGenerator(lexicon)
            val result = generator.generate("aaaaa", en) { cancelled }
            assertEquals(if (cancel) CandidateCompletion.CANCELLED else CandidateCompletion.READER_FAILURE, result.completion)
            assertEquals(64, result.verifiedTerminals)
            assertEquals(if (cancel) null else "aaaaa", result.original)
            assertTrue(result.alternatives.isEmpty())
            assertTrue(result.prohibitsAutoReplace)
            assertScratchCleared(generator)
            lexicon.afterStop = {}
            val reused = generator.generate("aaaaa", en)
            assertEquals(if (stateCap) CandidateCompletion.STATES_EXHAUSTED else CandidateCompletion.VERIFIED_EXHAUSTED,
                reused.completion)
            assertEquals(7, reused.alternatives.size)
            assertScratchCleared(generator)
        }
    }

    @Test
    fun `payload-bearing diagnostics redact original display and canonical key sentinels`() {
        val result = CandidateGenerator(ScriptedLexicon(mapOf(en to listOf(Entry("sentinel")))))
            .generate("sentinelx", en)
        val candidate = result.alternatives.single().copy(
            text = "DISPLAY_SENTINEL", canonicalKey = "KEY_SENTINEL", terminalKey = "TERMINAL_SENTINEL",
        )
        val snapshot = result.copy(original = "ORIGINAL_SENTINEL", alternatives = listOf(candidate))
        assertEquals("GeneratedCandidate(redacted)", candidate.toString())
        assertEquals("CandidateGeneration(completion=COMPLETE, candidateCount=1, redacted)", snapshot.toString())
        val nested = listOf(candidate, candidate.copy(), snapshot, snapshot.copy(), snapshot.alternatives).toString()
        for (sentinel in listOf("DISPLAY_SENTINEL", "KEY_SENTINEL", "TERMINAL_SENTINEL", "ORIGINAL_SENTINEL", "sentinelx", "sentinel")) {
            assertFalse(nested.contains(sentinel))
        }
    }

    @Test
    fun `unavailable exact or scan cannot publish a supposedly complete result`() {
        for (duringExact in listOf(true, false)) {
            val lexicon = ScriptedLexicon(mapOf(en to listOf(Entry("cat"))))
            if (duringExact) lexicon.unavailableExact = es else lexicon.unavailableScan = es
            val result = CandidateGenerator(lexicon).generate("cut", en)
            assertEquals(CandidateCompletion.UNAVAILABLE, result.completion)
            assertTrue(result.prohibitsAutoReplace)
            assertTrue(result.alternatives.isEmpty())
        }
    }

    @Test
    fun `reader contract violations fail closed and clear references`() {
        for (entry in listOf(Entry("CUT"), Entry("cut"), Entry("cats"), Entry("remote"), Entry("cat", 0),
            Entry("x".repeat(33)))) {
            val lexicon = ScriptedLexicon(mapOf(en to listOf(entry)))
            lexicon.emitWithoutAdmission = true
            val generator = CandidateGenerator(lexicon)
            val result = generator.generate("cut", en)
            assertEquals(CandidateCompletion.READER_FAILURE, result.completion)
            assertTrue(result.prohibitsAutoReplace)
            assertScratchCleared(generator)
        }
    }

    @Test
    fun `cancellation before during and after scan returns no payload and cleans reusable scratch`() {
        for (cancelAt in listOf(0, 1, 3)) {
            var cancelled = cancelAt == 0
            val lexicon = ScriptedLexicon(mapOf(en to listOf(Entry("cat"), Entry("cot"), Entry("cit"))))
            lexicon.afterVisit = { visits -> if (visits == cancelAt) cancelled = true }
            val generator = CandidateGenerator(lexicon)
            val result = generator.generate("cut", en) { cancelled }
            assertEquals(CandidateCompletion.CANCELLED, result.completion)
            assertNull(result.original)
            assertTrue(result.alternatives.isEmpty())
            assertTrue(result.prohibitsAutoReplace)
            assertScratchCleared(generator)
            lexicon.afterVisit = {}
            val reused = generator.generate("cut", en)
            assertEquals(CandidateCompletion.COMPLETE, reused.completion)
            assertEquals(3, reused.alternatives.size)
            assertScratchCleared(generator)
        }
    }

    @Test
    fun `reader exception after accepted candidate cleans scratch without retaining its message`() {
        val lexicon = ScriptedLexicon(mapOf(en to listOf(Entry("cat"))))
        lexicon.afterVisit = { throw IllegalStateException("fixture-only error") }
        val generator = CandidateGenerator(lexicon)
        val result = generator.generate("cut", en)
        assertEquals(CandidateCompletion.READER_FAILURE, result.completion)
        assertTrue(result.alternatives.isEmpty())
        assertScratchCleared(generator)
    }

    @Test
    fun `checked exact and scan exceptions become safe results and allow clean followup`() {
        for (duringExact in listOf(true, false)) for (cancel in listOf(true, false)) {
            var cancelled = false
            val fail: () -> Unit = {
                cancelled = cancel
                throw IOException("IO_PAYLOAD_SENTINEL")
            }
            val lexicon = ScriptedLexicon(mapOf(en to listOf(Entry("cat"))))
            if (duringExact) lexicon.afterExactRead = fail else lexicon.afterVisit = { fail() }
            val generator = CandidateGenerator(lexicon)
            val result = generator.generate("cut", en) { cancelled }
            assertEquals(if (cancel) CandidateCompletion.CANCELLED else CandidateCompletion.READER_FAILURE, result.completion)
            assertEquals(if (cancel) null else "cut", result.original)
            assertEquals(if (duringExact) 0 else 1, result.verifiedTerminals)
            assertTrue(result.alternatives.isEmpty())
            assertTrue(result.prohibitsAutoReplace)
            assertFalse(result.toString().contains("IO_PAYLOAD_SENTINEL"))
            assertScratchCleared(generator)
            lexicon.afterExactRead = {}
            lexicon.afterVisit = {}
            val reused = generator.generate("cut", en)
            assertEquals(CandidateCompletion.COMPLETE, reused.completion)
            assertEquals(listOf("cat"), reused.alternatives.map { it.text })
            assertScratchCleared(generator)
        }
    }

    @Test
    fun `interrupted reader work preserves thread interrupt and returns cancelled without payload`() {
        for (duringExact in listOf(true, false)) {
            assertFalse(Thread.currentThread().isInterrupted)
            val lexicon = ScriptedLexicon(mapOf(en to listOf(Entry("cat"))))
            val interrupt: () -> Unit = { throw InterruptedException("INTERRUPT_SENTINEL") }
            if (duringExact) lexicon.afterExactRead = interrupt else lexicon.afterVisit = { interrupt() }
            val generator = CandidateGenerator(lexicon)
            try {
                val result = generator.generate("cut", en)
                assertEquals(CandidateCompletion.CANCELLED, result.completion)
                assertNull(result.original)
                assertTrue(result.alternatives.isEmpty())
                assertTrue(Thread.currentThread().isInterrupted)
                assertScratchCleared(generator)
                val reads = lexicon.exactCalls
                assertEquals(CandidateCompletion.CANCELLED, generator.generate("cut", en).completion)
                assertEquals(reads, lexicon.exactCalls)
            } finally {
                Thread.interrupted() // Test owns this signal; do not contaminate the JUnit runner.
            }
            lexicon.afterExactRead = {}
            lexicon.afterVisit = {}
            assertEquals(CandidateCompletion.COMPLETE, generator.generate("cut", en).completion)
            assertScratchCleared(generator)
        }
    }

    @Test
    fun `fatal error propagates while finally releases owned candidate scratch`() {
        val lexicon = ScriptedLexicon(mapOf(en to listOf(Entry("cat"))))
        val error = LinkageError("FATAL_SENTINEL")
        lexicon.afterVisit = { throw error }
        val generator = CandidateGenerator(lexicon)
        assertSame(error, assertThrows(LinkageError::class.java) { generator.generate("cut", en) })
        assertScratchCleared(generator)
        lexicon.afterVisit = {}
        assertEquals(CandidateCompletion.COMPLETE, generator.generate("cut", en).completion)
    }

    private fun neighborWords(): List<String> = (0..2).flatMap { position ->
        ('b'..'z').map { letter -> "aaaaa".replaceRange(position, position + 1, letter.toString()) }
    }

    private fun partialDictionaries(): Pair<List<Entry>, List<Entry>> {
        val ordinary = neighborWords().filter { word -> word.none { it in "qwsz" } }
        val primary = ordinary.take(50).map { Entry(it, 100) }
        val adjacent = (0..2).flatMap { position ->
            "qs".map { letter -> Entry("aaaaa".replaceRange(position, position + 1, letter.toString()), 1) }
        }
        // 50 primary + 4 cross-language duplicates + 6 cheap fallback + 4 ordinary = 64 verified.
        // The next fallback terminal requires work beyond either cap, so neither result is complete.
        val fallback = primary.take(4) + adjacent + ordinary.drop(50).take(5).map { Entry(it, 1) }
        return primary to fallback
    }

    private fun assertScratchCleared(generator: CandidateGenerator) {
        for (field in generator.javaClass.declaredFields) {
            field.isAccessible = true
            val value = field.get(generator)
            if (value is Array<*>) assertTrue(value.all { it == null })
            if (value is WeightedDamerauLevenshtein) {
                for (array in value.javaClass.declaredFields.filter { it.type == IntArray::class.java }) {
                    array.isAccessible = true
                    assertTrue((array.get(value) as IntArray).all { it == 0 })
                }
            }
        }
    }
}

internal data class Entry(val word: String, val rank: Int = Int.MAX_VALUE)

/**
 * Real small in-memory lexicon, intentionally a flat fixture scan, not a proposed production reader.
 * Extra numeric states script exact boundary cases. Unit filtering uses the integrated unit engine;
 * a separate shortest-edit-graph oracle below checks full admission/ranking independently.
 */
internal class ScriptedLexicon(val entries: Map<KeyboardLanguage, List<Entry>>) : CandidateLexicon {
    private val membership = entries.mapValues { (_, words) -> words.map { it.word }.toHashSet() }
    val scanned = mutableListOf<KeyboardLanguage>()
    val exactStates = mutableMapOf<KeyboardLanguage, Int>()
    val scanPrefixStates = mutableMapOf<KeyboardLanguage, Int>()
    var exactCalls = 0
    var unavailableExact: KeyboardLanguage? = null
    var unavailableScan: KeyboardLanguage? = null
    var emitWithoutAdmission = false
    var afterExactRead: () -> Unit = {}
    var afterVisit: (Int) -> Unit = {}
    var afterStop: () -> Unit = {}
    private val unit = WeightedDamerauLevenshtein(EditCostProfile.UNIT)

    override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
        exactCalls++
        repeat(exactStates[language] ?: 1) {
            if (!control.inspectState()) return ExactMembership.UNAVAILABLE
        }
        afterExactRead()
        if (unavailableExact == language) return ExactMembership.UNAVAILABLE
        if (emitWithoutAdmission) return ExactMembership.ABSENT
        return if (membership[language].orEmpty().contains(key)) ExactMembership.PRESENT else ExactMembership.ABSENT
    }

    override fun scan(
        language: KeyboardLanguage, key: String, unitRadius: Int,
        control: CandidateSearchControl, visitor: CandidateVisitor,
    ): LexiconScanStatus {
        scanned.add(language)
        repeat(scanPrefixStates[language] ?: 0) {
            if (!control.inspectState()) return stopped()
        }
        if (unavailableScan == language) return LexiconScanStatus.UNAVAILABLE
        var visits = 0
        for (entry in entries[language].orEmpty()) {
            if (!control.inspectState()) return stopped()
            if (emitWithoutAdmission || (entry.word != key && unit.features(key, entry.word, language).editCost <= unitRadius)) {
                if (!visitor.visit(entry.word, entry.rank)) return stopped()
                afterVisit(++visits)
            }
            if (!control.checkpoint()) return stopped()
        }
        return LexiconScanStatus.COMPLETE
    }

    private fun stopped(): LexiconScanStatus {
        afterStop()
        return LexiconScanStatus.UNAVAILABLE
    }
}

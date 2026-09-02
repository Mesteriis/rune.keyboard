package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.util.PriorityQueue
import org.junit.Assert.*
import org.junit.Test

class WeightedDamerauLevenshteinTest {
    private val en = KeyboardLanguage.ENGLISH

    @Test
    fun `unit profile includes unrestricted transpositions rather than OSA`() {
        val distance = WeightedDamerauLevenshtein(EditCostProfile.UNIT)
        assertEquals(2.0, distance.features("CA", "ABC", en).editCost, 0.0)
        assertEquals(1.0, distance.features("ab", "ba", en).editCost, 0.0)
        assertEquals(2.0, distance.features("a cat", "an act", en).editCost, 0.0)
        assertEquals(3.0, distance.features("kitten", "sitting", en).editCost, 0.0)
    }

    @Test
    fun `initial costs cover insertion deletion ordinary and adjacent substitution`() {
        val distance = WeightedDamerauLevenshtein()
        assertEquals(1.0, distance.features("cat", "cats", en).editCost, 0.0)
        assertEquals(1.0, distance.features("cats", "cat", en).editCost, 0.0)
        assertEquals(1.0, distance.features("a", "p", en).editCost, 0.0)
        assertEquals(0.75, distance.features("a", "s", en).editCost, 0.0)
        assertEquals(1.25, distance.features("ab", "ba", en).editCost, 0.0)
        assertEquals(2.0, distance.features("ad", "dw", en).editCost, 0.0)
    }

    @Test
    fun `keyboard neighbourhood is static symmetric and language specific`() {
        assertTrue(KeyboardDistance.areAdjacent('q'.code, 'a'.code, en))
        assertTrue(KeyboardDistance.areAdjacent('a'.code, 'q'.code, en))
        assertFalse(KeyboardDistance.areAdjacent('q'.code, 'z'.code, en))
        assertFalse(KeyboardDistance.areAdjacent('a'.code, 'a'.code, en))
        assertTrue(KeyboardDistance.areAdjacent('л'.code, 'д'.code, KeyboardLanguage.RUSSIAN))
        assertTrue(KeyboardDistance.areAdjacent('l'.code, 'ñ'.code, KeyboardLanguage.SPANISH))
        assertFalse(KeyboardDistance.areAdjacent('l'.code, 'ñ'.code, en))
        assertFalse(KeyboardDistance.areAdjacent(0x10061, 's'.code, en))
        assertEquals(0.75, WeightedDamerauLevenshtein().features("л", "д", KeyboardLanguage.RUSSIAN).editCost, 0.0)
    }

    @Test
    fun `repetition is an explicit separate feature with no negative edit costs`() {
        val distance = WeightedDamerauLevenshtein()
        val one = distance.features("helllo", "hello", en)
        assertEquals(1.0, one.editCost, 0.0)
        assertEquals(1, one.repeatedCharacterEdits)
        assertEquals(0.25, one.repetitionBonus, 0.0)
        val several = distance.features("aaabb", "abbbb", en)
        assertEquals(4, several.repeatedCharacterEdits)
        assertEquals(1.0, several.repetitionBonus, 0.0)
        assertEquals(0, distance.features("helllo", "help", en).repeatedCharacterEdits)
        assertEquals(0, distance.features("", "aaa", en).repeatedCharacterEdits)
    }

    @Test
    fun `NFC and case equivalence preserve Russian and Spanish distinctions`() {
        val distance = WeightedDamerauLevenshtein()
        for ((left, right) in listOf("é" to "e\u0301", "Ñ" to "n\u0303", "Ё" to "е\u0308", "HELLO" to "hello")) {
            assertEquals(0.0, distance.features(left, right, en).editCost, 0.0)
        }
        for ((left, right) in listOf("е" to "ё", "n" to "ñ", "esta" to "está", "ü" to "u")) {
            assertTrue(distance.features(left, right, en).editCost > 0.0)
        }
    }

    @Test
    fun `supplementary Unicode counts as one scalar and transposes as one unit`() {
        val distance = WeightedDamerauLevenshtein(EditCostProfile.UNIT)
        assertEquals(1.0, distance.features("😀", "", en).editCost, 0.0)
        assertEquals(1.0, distance.features("😀a", "a😀", en).editCost, 0.0)
        assertEquals(0.0, distance.features("𐐀", "𐐨", en).editCost, 0.0)
        assertEquals(32.0, distance.features("😀".repeat(32), "", en).editCost, 0.0)
    }

    @Test
    fun `strict input bounds reject malformed long and normalization expansion inputs`() {
        val distance = WeightedDamerauLevenshtein()
        for (token in listOf("a".repeat(33), "😀".repeat(33), "\uD800", "\uDC00", "a" + "\u0344".repeat(31), "İ" + "a".repeat(31))) {
            assertThrows(IllegalArgumentException::class.java) { distance.features(token, "ok", en) }
            assertThrows(IllegalArgumentException::class.java) { distance.features("ok", token, en) }
        }
        assertEquals(0.0, distance.features("a".repeat(32), "a".repeat(32), en).editCost, 0.0)
    }

    @Test
    fun `scratch is reusable and clears token scalars on success and failure`() {
        val distance = WeightedDamerauLevenshtein()
        repeat(20) {
            assertEquals(1.25, distance.features("private", "pirvate", en).editCost, 0.0)
            assertEquals(0.0, distance.features("", "", en).editCost, 0.0)
        }
        assertThrows(IllegalArgumentException::class.java) { distance.features("private", "x".repeat(33), en) }
        for (field in distance.javaClass.declaredFields.filter { it.type == IntArray::class.java }) {
            field.isAccessible = true
            assertTrue((field.get(distance) as IntArray).all { it == 0 })
        }
    }

    @Test
    fun `DP matches independent shortest edit path oracle on two small alphabets`() {
        // 2 alphabets * 2 profiles * 40 source strings * 40 targets = 6,400 exact comparisons.
        // Oracle uses graph edits, never the DP recurrence or production adjacency implementation.
        var compared = 0
        for (alphabet in listOf("asd", "adw")) {
            val words = words(alphabet, 3)
            for (profile in EditCostProfile.entries) {
                val distance = WeightedDamerauLevenshtein(profile)
                for (source in words) {
                    val oracle = shortestEdits(source, alphabet, profile == EditCostProfile.UNIT)
                    for (target in words) {
                        val actual = distance.features(source, target, en).editCost
                        assertEquals("oracle mismatch for profile $profile", oracle.getValue(target) / 4.0, actual, 0.0)
                        assertTrue(actual.isFinite() && actual >= 0.0)
                        compared++
                    }
                }
            }
        }
        assertEquals(6_400, compared)
    }

    private fun words(alphabet: String, maximum: Int): List<String> {
        val all = mutableListOf("")
        var level = listOf("")
        repeat(maximum) {
            level = level.flatMap { word -> alphabet.map { word + it } }
            all += level
        }
        return all
    }

    private data class Step(val text: String, val cost: Int)

    private fun shortestEdits(source: String, alphabet: String, unit: Boolean): Map<String, Int> {
        val best = mutableMapOf(source to 0)
        val pending = PriorityQueue<Step>(compareBy { it.cost })
        pending.add(Step(source, 0))
        while (pending.isNotEmpty()) {
            val (word, cost) = pending.remove()
            if (best[word] != cost) continue
            fun offer(next: String, weight: Int) {
                val total = cost + weight
                if (total < best.getOrDefault(next, Int.MAX_VALUE)) {
                    best[next] = total
                    pending.add(Step(next, total))
                }
            }
            for (i in word.indices) {
                offer(word.removeRange(i, i + 1), 4)
                for (letter in alphabet) if (letter != word[i]) {
                    val adjacent = setOf(word[i], letter) in listOf(setOf('a', 's'), setOf('s', 'd'), setOf('a', 'w'))
                    offer(word.replaceRange(i, i + 1, letter.toString()), if (!unit && adjacent) 3 else 4)
                }
                if (i + 1 < word.length && word[i] != word[i + 1]) {
                    offer(word.substring(0, i) + word[i + 1] + word[i] + word.substring(i + 2), if (unit) 4 else 5)
                }
            }
            // Sources/targets have length <=3 and a <=12 quarter-unit direct path.
            // Visiting length 5 needs >=16 insertion/deletion units, so length 4 is exhaustive.
            if (word.length < 4) for (i in 0..word.length) for (letter in alphabet) {
                offer(word.substring(0, i) + letter + word.substring(i), 4)
            }
        }
        return best
    }
}

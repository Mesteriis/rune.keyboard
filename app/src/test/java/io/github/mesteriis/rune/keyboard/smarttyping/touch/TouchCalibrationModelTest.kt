package io.github.mesteriis.rune.keyboard.smarttyping.touch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TouchCalibrationModelTest {
    private val profile = TouchLayoutProfile("ENGLISH", "LETTERS", 1080, 800, 1, 360, 800, 420, 0, "a".repeat(64))
    private fun sample(profile: TouchLayoutProfile = this.profile, observed: Char = 's', x: Double = -0.4) =
        PhysicalTouchSample(profile, observed, listOf(TouchKeyOffset('s', x, 0.1), TouchKeyOffset('a', x + 1, 0.1)))
    private fun model() = TouchCalibrationModel().apply { setEnabled(true) }
    private fun train(model: TouchCalibrationModel, count: Int, intended: String = "a", x: Double = -0.4) {
        repeat(count) {
            model.observe(sample(x = x))
            assertTrue(model.confirmWord("s", intended))
        }
    }

    @Test fun `observing and ranking cannot train`() {
        val model = model()
        model.observe(sample())
        assertEquals(0.0, model.candidateBonus("s", "a"), 0.0)
        assertEquals("RUNE_TOUCH_1\n", model.encodeSnapshot())
        model.clearPending()
        assertFalse(model.confirmWord("s", "a"))
    }

    @Test fun `requires minimum confirmed samples and applies shrinkage`() {
        val model = model()
        train(model, TouchCalibrationModel.MIN_SAMPLES - 1)
        model.observe(sample())
        assertEquals(0.0, model.candidateBonus("s", "a"), 0.0)
        assertTrue(model.confirmWord("s", "a"))
        model.observe(sample())
        val bonus = model.candidateBonus("s", "a")
        assertTrue(bonus > 0.0)
        assertTrue(bonus < 0.04)
        assertEquals(0.0, model.candidateBonus("s", "as"), 0.0)
    }

    @Test fun `explicit choice of original word also trains`() {
        val model = model()
        train(model, 6, intended = "s")
        model.observe(sample())
        assertTrue(model.candidateBonus("s", "a") < 0.0)
    }

    @Test fun `disabled learning erases pending and cannot train or rank`() {
        val model = model()
        train(model, 6)
        model.observe(sample())
        val snapshot = model.encodeSnapshot()
        model.setEnabled(false)
        assertFalse(model.confirmWord("s", "a"))
        assertEquals(0.0, model.candidateBonus("s", "a"), 0.0)
        model.observe(sample())
        assertEquals(snapshot, model.encodeSnapshot())
        model.setEnabled(true)
        assertFalse(model.confirmWord("s", "a"))
    }

    @Test fun `geometry language orientation and Fold screen profiles stay separate`() {
        val model = model()
        train(model, 8)
        listOf(profile.copy(widthPx = 900), profile.copy(heightPx = 700),
            profile.copy(language = "RUSSIAN"), profile.copy(orientation = 2),
            profile.copy(screenWidthDp = 600), profile.copy(screenHeightDp = 600),
            profile.copy(displayId = 1), profile.copy(densityDpi = 320),
            profile.copy(geometrySignature = "b".repeat(64))).forEach {
            model.clearPending()
            model.observe(sample(profile = it))
            assertEquals(0.0, model.candidateBonus("s", "a"), 0.0)
        }
        model.clearPending()
        model.observe(sample())
        model.observe(sample(profile = profile.copy(widthPx = 900)))
        assertFalse(model.confirmWord("ss", "aa"))
    }

    @Test fun `unmatched words insertions deletions and unobserved intended keys do not train`() {
        val model = model()
        listOf("s" to "aa", "ss" to "a", "a" to "s", "s" to "z").forEach { (raw, intended) ->
            model.observe(sample())
            assertFalse(model.confirmWord(raw, intended))
        }
        assertEquals("RUNE_TOUCH_1\n", model.encodeSnapshot())
    }

    @Test fun `outliers do not shift trained mean and count saturates`() {
        val model = model()
        train(model, 100)
        val snapshot = model.encodeSnapshot()
        assertTrue(snapshot.contains("\t64\t"))
        model.observe(sample(x = 0.5))
        assertFalse(model.confirmWord("s", "a"))
        assertEquals(snapshot, model.encodeSnapshot())
        model.observe(sample(x = -1.3))
        assertFalse(model.confirmWord("s", "a"))
        assertEquals(snapshot, model.encodeSnapshot())
    }

    @Test fun `invalid and overflow samples cannot become a suffix word`() {
        val model = model()
        repeat(TouchCalibrationModel.MAX_WORD_LENGTH + 1) { model.observe(sample()) }
        assertFalse(model.confirmWord("s", "a"))
        model.observe(sample())
        model.observe(sample(x = Double.NaN))
        assertFalse(model.confirmWord("s", "a"))
    }

    @Test fun `aggregate codec round trips without pending samples and rejects malformed data atomically`() {
        val model = model()
        train(model, 8)
        model.observe(sample())
        val snapshot = model.encodeSnapshot()
        val restored = model()
        assertTrue(restored.restoreSnapshot(snapshot))
        assertFalse(restored.confirmWord("s", "a"))
        restored.observe(sample())
        assertEquals(model.candidateBonus("s", "a"), restored.candidateBonus("s", "a"), 0.0)
        listOf("", snapshot.replace("RUNE_TOUCH_1", "RUNE_TOUCH_2"),
            snapshot.replace("\t8\t", "\t1000\t"), snapshot.replace("0.6", "NaN"),
            snapshot + snapshot.lineSequence().drop(1).first() + "\n",
            "x".repeat(TouchCalibrationModel.MAX_SNAPSHOT_BYTES + 1)).forEach {
            assertFalse(restored.restoreSnapshot(it))
            assertEquals(snapshot, restored.encodeSnapshot())
        }
        restored.reset()
        assertEquals("RUNE_TOUCH_1\n", restored.encodeSnapshot())
    }

    @Test fun `profile count and aggregate snapshot size stay bounded`() {
        val model = model()
        repeat(TouchCalibrationModel.MAX_PROFILES + 2) {
            model.observe(sample(profile = profile.copy(widthPx = 500 + it)))
            assertTrue(model.confirmWord("s", "a"))
        }
        assertEquals(TouchCalibrationModel.MAX_PROFILES, model.encodeSnapshot().lineSequence().count { it.contains('\t') })
        assertTrue(model.encodeSnapshot().length <= TouchCalibrationModel.MAX_SNAPSHOT_BYTES)
    }
}

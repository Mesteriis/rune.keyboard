package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.graphics.Rect
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import org.junit.Assert.*
import org.junit.After
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test

/** Explicit physical run only: actual touch events, real remote InputConnection, public test text. */
class FoldAutocorrectionInstrumentedTest {
    private val driver = ImeTestDriver()
    private var prepared = false
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val field = "qa_composing_text"

    @Before fun isolateSyntheticFeedback() {
        // Skip ordinary CI before any IME/settings mutation. Physical failures never capture pixels/trees.
        assumeTrue("Explicit physical Fold test required",
            InstrumentationRegistry.getArguments().getString("allowPhysicalDevice") == "true" &&
                Build.MODEL.startsWith("SM-F"))
        prepared = true
        driver.setUp()
        val edit = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
        for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
            SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS, SettingsCodec.KEY_DYNAMIC_TOUCH,
            SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, SettingsCodec.KEY_QUALITY_METRICS,
            SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES)) edit.putBoolean(key, false)
        check(edit.putBoolean(SettingsCodec.KEY_VISIBLE_UNDO, true).commit())
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
    }

    @get:org.junit.Rule val testName = org.junit.rules.TestName()

    @After fun restoreOwnerSettings() {
        if (prepared) try {
            // Preserve the failing test's bounded journal before subsequent tests rotate it away.
            // App-private cache only; no screenshots, editor reads or diagnostic consent changes.
            val recorder = io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider
                .create(context) as io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsRecorder
            val done = java.util.concurrent.CountDownLatch(1)
            var flushed = false
            recorder.barrier { flushed = it; done.countDown() }
            check(done.await(3, java.util.concurrent.TimeUnit.SECONDS) && flushed)
            val name = "${testName.methodName}-${SystemClock.uptimeMillis()}"
            val output = java.io.File(context.cacheDir, "fold-autocorrection-journals/$name")
            check(output.mkdirs())
            for (stream in io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticStream.entries) {
                val exported = java.util.concurrent.CountDownLatch(1)
                var success = false
                recorder.export(recorder.newExport(), stream, {
                    java.io.FileOutputStream(java.io.File(output, "${stream.name.lowercase()}.jsonl"))
                }, { success = it; exported.countDown() })
                check(exported.await(5, java.util.concurrent.TimeUnit.SECONDS) && success)
            }
            instrumentation.sendStatus(0, Bundle().apply { putString("journal_snapshot", name) })
        } finally {
            driver.tearDown()
        }
    }

    private fun fresh() = driver.launchComposingQa(language = KeyboardLanguage.RUSSIAN)
    private fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
    private fun text() = checkNotNull(driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, field))).text.orEmpty()
    private fun touchOwnQaKey(bounds: Rect) {
        // UiDevice.currentPackageName waits for accessibility idle and would slow every key.
        // Observe only the active root package so the requested typing cadence is preserved.
        val active = instrumentation.uiAutomation.rootInActiveWindow
        val foreground = active?.packageName?.toString()
        @Suppress("DEPRECATION")
        active?.recycle()
        check(foreground == ImeTestDriver.PACKAGE_NAME) { "Physical QA lost foreground to $foreground" }
        val touch = driver.touchDown(bounds); var released = false
        try { driver.releaseTouch(touch); released = true }
        finally { if (!released) driver.cancelTouch(touch) }
    }

    private fun noReadback() {
        val stats = checkNotNull(driver.device.wait(Until.findObject(
            By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats")), 3000)) {
            "QA counters unavailable; foreground=${driver.device.currentPackageName}"
        }.text.split(' ').associate { val (key, value) = it.split('='); key to value.toInt() }
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected editor payload read: $name", 0, stats.getValue(name))
    }
    private fun report(case: String, typed: String, expected: String, actual: String, elapsed: Long = 0) {
        instrumentation.sendStatus(0, Bundle().apply {
            putString("fold_case", case); putString("typed", typed); putString("expected", expected)
            putString("actual", actual); putBoolean("matched", expected == actual); putLong("elapsed_ms", elapsed)
        })
    }

    @Test fun diagnosticRecordingSurvivesManualFocusAndKeyboardReshow() {
        val recorder = io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider
            .create(context) as io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsRecorder
        fun flush() {
            val done = java.util.concurrent.CountDownLatch(1)
            var success = false
            recorder.barrier { success = it; done.countDown() }
            check(done.await(3, java.util.concurrent.TimeUnit.SECONDS) && success)
        }
        fun inputs(): Map<String, Int> {
            flush()
            return (0..3).flatMap { index ->
                val file = java.io.File(context.noBackupFilesDir, "typing-diagnostics/text.$index.jsonl")
                if (!file.exists()) emptyList() else {
                    check(file.length() <= 1_048_576)
                    file.readLines().filter { line -> org.json.JSONObject(line).optString("kind") == "INPUT" }
                }
            }.groupingBy { it }.eachCount()
        }
        flush()
        assumeTrue("Existing explicit text-diagnostics consent required", recorder.preferences.text)
        fun checkpoint(phase: String) {
            var owner: Context = keyboardSnapshot().keyboard.rootView.context
            while (owner is android.content.ContextWrapper && owner !is io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService)
                owner = owner.baseContext
            val service = owner as io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService
            val values = Bundle()
            instrumentation.runOnMainSync {
                val controller = service.javaClass.getDeclaredField("typingSession").apply { isAccessible = true }
                    .get(service) as io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
                values.putString("diagnostic_checkpoint", phase)
                values.putBoolean("typing_enabled", controller.state.enabled)
                values.putInt("owned_context_length", controller.state.contextText.length)
                values.putBoolean("diagnostic_closed", controller.javaClass.getDeclaredField("diagnosticSegmentClosed")
                    .apply { isAccessible = true }.getBoolean(controller))
                values.putBoolean("recorder_has_session", recorder.javaClass.getDeclaredField("session")
                    .apply { isAccessible = true }.get(recorder) != null)
            }
            instrumentation.sendStatus(0, values)
        }
        val failures = mutableListOf<String>()
        for (phase in listOf("fresh", "tap-empty", "reshow")) {
            fresh(); checkpoint("$phase-ready")
            if (phase == "tap-empty") driver.focusField(field)
            if (phase == "reshow") { driver.device.pressBack(); driver.focusField(field) }
            checkpoint("$phase-focused")
            val before = inputs()
            "журнал".forEach { driver.tapKey(it.toString()) }
            driver.awaitFieldText(field, "журнал")
            val count = inputs().entries.sumOf { (line, count) -> (count - (before[line] ?: 0)).coerceAtLeast(0) }
            instrumentation.sendStatus(0, Bundle().apply {
                putString("diagnostic_phase", phase); putInt("recorded_inputs", count)
            })
            if (count != 6) failures += "$phase=$count"
            noReadback()
        }
        assertTrue("Missing diagnostic input events: ${failures.joinToString()}", failures.isEmpty())
    }

    @Test fun extraBackspacesInEmptyFieldKeepTheWholeNextWord() {
        for (eraseOwnedWord in listOf(false, true)) {
            fresh()
            if (eraseOwnedWord) {
                "тест".forEach { driver.tapKey(it.toString()) }
                repeat(4) { driver.tapDelete() }
                // UiAutomator exposes this editor's hint as text when it is empty. The exact
                // next word below verifies that all four characters were actually removed.
            }
            repeat(3) { driver.tapDelete() }
            "зочу".forEach { driver.tapKey(it.toString()) }
            driver.awaitFieldText(field, "зочу")
            space()
            driver.awaitFieldText(field, "хочу ")
            driver.tapDelete()
            driver.awaitFieldText(field, "зочу")
            report("empty-backspace-$eraseOwnedWord", "зочу", "зочу", text())
            noReadback()
        }
    }

    /** Characterization: mismatches are reported as data, not silently accepted as correct. */
    @Test fun probePhrasesThroughRealTouchInput() {
        val cases = listOf(
            "я зочу домой " to "я хочу домой ",
            "ссын идет домой " to "сын идет домой ",
            "сегодя хорошая погода " to "сегодня хорошая погода ",
            "давай встретимся завтро " to "давай встретимся завтра ",
            "я прийду через пять минут " to "я приду через пять минут ",
            "это оченб важный вопрос " to "это очень важный вопрос ",
            "можно пожалуста воды " to "можно пожалуйста воды ",
            "мы скороо вернемся домой " to "мы скоро вернемся домой ",
            "спосибо за помощь " to "спасибо за помощь ",
            "проверь сообшение перед отправкой " to "проверь сообщение перед отправкой ",
            "нужен новй пароль " to "нужен новый пароль ",
            "нужно заберай вещи " to "нужно забирай вещи ",
            "мама дома и все хорошо " to "мама дома и все хорошо ",
            "мы будим детей утром " to "мы будим детей утром ",
            "это мой конь и новый пароль " to "это мой конь и новый пароль ")
        probeCases(cases, "phrase-probe-taps")
    }

    /** Authored fresh inputs; intentions are frozen before observing results. */
    @Test fun probeFreshEverydayPhrasesThroughRealTouchInput() {
        val cases = listOf(
            "передай привкт сестре " to "передай привет сестре ",
            "я уже ддмой и жду тебя " to "я уже домой и жду тебя ",
            "скажи куа идти дальше " to "скажи куда идти дальше ",
            "мы поггорим после встречи " to "мы поговорим после встречи ",
            "мне нуден другой пароль " to "мне нужен другой пароль ",
            "я буду черкз пять минут " to "я буду через пять минут ",
            "сейчас будкт немного времени " to "сейчас будет немного времени ",
            "проверь пожалуйсиа письмо " to "проверь пожалуйста письмо ",
            "мы встретимсч возле дома " to "мы встретимся возле дома ",
            "я не зеаю ответа " to "я не знаю ответа ",
            "ты можешь позвоеить позже " to "ты можешь позвонить позже ",
            "нужно купитб молоко " to "нужно купить молоко ",
            "я отправил сообшения вчера " to "я отправил сообщения вчера ",
            "сейчас всее работает хорошо " to "сейчас все работает хорошо ",
            "я очень рал тебя видеть " to "я очень рад тебя видеть ",
            "поставь стакан на сттл " to "поставь стакан на стол ",
            "завтра хорошая погода " to "завтра хорошая погода ",
            "это новая книга " to "это новая книга ",
            "мы ели суп " to "мы ели суп ",
            "это мои вещи " to "это мои вещи ",
            "он платит дань памяти " to "он платит дань памяти ",
            "оставь эту грань видимой " to "оставь эту грань видимой ",
            "мне нужен новй код " to "мне нужен новый код ",
            "давай встретимся завтро утром " to "давай встретимся завтра утром ")
        probeCases(cases, "fresh-phrase-probe-taps")
    }

    private fun probeCases(cases: List<Pair<String, String>>, label: String) {
        val arguments = InstrumentationRegistry.getArguments()
        val offset = arguments.getString("runePhraseOffset")?.toInt() ?: 0
        val count = arguments.getString("runePhraseCount")?.toInt() ?: cases.size
        require(offset in cases.indices && count in 1..cases.size && offset + count <= cases.size)
        for ((typed, expected) in cases.drop(offset).take(count)) {
            fresh()
            val started = SystemClock.uptimeMillis()
            val bounds = typed.toSet().associateWith { char -> Rect(if (char == ' ')
                checkNotNull(driver.device.findObject(By.desc(context.getString(R.string.key_space)))).visibleBounds
                else driver.characterKey(char.toString()).visibleBounds) }
            for (char in typed) {
                touchOwnQaKey(bounds.getValue(char))
                SystemClock.sleep(100)
            }
            SystemClock.sleep(500)
            report(label, typed, expected, text(), SystemClock.uptimeMillis() - started)
            noReadback()
        }
    }

    @Test fun learnedContextualCorrectionsAtTwoPacesPreserveExactUndo() {
        val resources = io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingResources.get(context)
        val deadline = SystemClock.uptimeMillis() + 60_000L
        while ((!resources.experiments.contextualReady || !resources.dictionaryLoaded ||
                !resources.controls.isReady || !resources.personal.isReady) && SystemClock.uptimeMillis() < deadline)
            SystemClock.sleep(50)
        assertTrue("Contextual resources unavailable", resources.experiments.contextualReady && resources.dictionaryLoaded)
        assertTrue("Original-protection stores unavailable", resources.controls.isReady && resources.personal.isReady)
        val cases = listOf("я плоец " to "я пловец ", "я всоал " to "я встал ",
            "я пытаюс " to "я пытаюсь ", "он дьявл " to "он дьявол ",
            "в стаьье " to "в статье ", "ты помвл " to "ты помыл ",
            "нужен новй " to "нужен новый ", "сейчас всее " to "сейчас все ",
            "это новая книга " to "это новая книга ", "мы видели всех " to "мы видели всех ")
        for (pause in listOf(50L, 100L)) for ((typed, expected) in cases) {
            fresh()
            val bounds = typed.toSet().associateWith { char -> Rect(if (char == ' ')
                checkNotNull(driver.device.findObject(By.desc(context.getString(R.string.key_space)))).visibleBounds
                else driver.characterKey(char.toString()).visibleBounds) }
            val started = SystemClock.uptimeMillis()
            for (char in typed) { touchOwnQaKey(bounds.getValue(char)); SystemClock.sleep(pause) }
            driver.awaitFieldText(field, expected)
            report("learned-context-$pause", typed, expected, text(), SystemClock.uptimeMillis() - started)
            if (typed != expected) { driver.tapDelete(); driver.awaitFieldText(field, typed.trimEnd()) }
            noReadback()
        }
    }

    @Test fun contextualInternalEditsKeepWordFormsAndExactUndoAtTwoPaces() {
        val cases = listOf("нужен новй " to "нужен новый ",
            "мне нужен новй " to "мне нужен новый ",
            "давай встретимся завтро " to "давай встретимся завтра ",
            "начнем с новой " to "начнем с новой ",
            "говорим о новой " to "говорим о новой ",
            "для новой " to "для новой ")
        for (pause in listOf(50L, 100L)) for ((typed, expected) in cases) {
            fresh()
            val bounds = typed.toSet().associateWith { char -> Rect(if (char == ' ')
                checkNotNull(driver.device.findObject(By.desc(context.getString(R.string.key_space)))).visibleBounds
                else driver.characterKey(char.toString()).visibleBounds) }
            val started = SystemClock.uptimeMillis()
            for (char in typed) {
                touchOwnQaKey(bounds.getValue(char))
                SystemClock.sleep(pause)
            }
            driver.awaitFieldText(field, expected)
            report("word-context-$pause", typed, expected, text(), SystemClock.uptimeMillis() - started)
            if (typed != expected) {
                driver.tapDelete()
                driver.awaitFieldText(field, typed.trimEnd())
            }
            noReadback()
        }
    }

    @Test fun freshReviewedCorrectionsAtTwoPacesWithExactUndo() {
        val cases = listOf("я уже ддмой " to "я уже домой ", "сейчас всее " to "сейчас все ",
            "я уже домой " to "я уже домой ", "мы видели всех " to "мы видели всех ")
        for (pause in listOf(50L, 100L)) for ((typed, expected) in cases) {
            fresh()
            val bounds = typed.toSet().associateWith { char -> Rect(if (char == ' ')
                checkNotNull(driver.device.findObject(By.desc(context.getString(R.string.key_space)))).visibleBounds
                else driver.characterKey(char.toString()).visibleBounds) }
            for (char in typed) { touchOwnQaKey(bounds.getValue(char)); SystemClock.sleep(pause) }
            driver.awaitFieldText(field, expected)
            report("fresh-reviewed-$pause", typed, expected, text())
            if (typed != expected) { driver.tapDelete(); driver.awaitFieldText(field, typed.trimEnd()) }
            noReadback()
        }
    }

    @Test fun validWordManualAlternativesNeverBecomeAutomatic() {
        val preferences = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE)
        fun configure(enabled: Boolean) {
            check(preferences.edit().putBoolean(SettingsCodec.KEY_MANUAL_CANDIDATE_EXPANSION, enabled).commit())
            instrumentation.waitForIdleSync()
        }
        val suggestion = By.desc(context.getString(R.string.candidate_correction, "нужен"))
        configure(false); fresh(); "нуден".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(field, "нуден"); SystemClock.sleep(350)
        assertNull(driver.device.findObject(suggestion))
        space(); driver.awaitFieldText(field, "нуден "); noReadback()
        configure(true); fresh(); "нуден".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(field, "нуден")
        val candidate = checkNotNull(driver.device.wait(Until.findObject(suggestion), 5000))
        assertEquals("нужен", candidate.text)
        space(); driver.awaitFieldText(field, "нуден "); noReadback()
        fresh(); "нуден".forEach { driver.tapKey(it.toString()) }
        checkNotNull(driver.device.wait(Until.findObject(suggestion), 5000)).click()
        driver.awaitFieldText(field, "нужен")
        checkNotNull(driver.device.wait(Until.findObject(
            By.desc(context.getString(R.string.candidate_original, "нуден"))), 5000)).click()
        driver.awaitFieldText(field, "нуден")
        space(); driver.awaitFieldText(field, "нуден ")
        report("valid-word-explicit-only", "нуден", "нуден ", text()); noReadback()
    }

    @android.annotation.SuppressLint("ClickableViewAccessibility") // Observe only; original touch handler performs clicks.
    @Test fun repeatedRealTouchInputAndUndoKeepTheRequestedCharacters() {
        val rounds = InstrumentationRegistry.getArguments().getString("runeForensicRounds")?.toInt() ?: 12
        require(rounds in 1..24)
        val cases = listOf("спосибо " to "спасибо ",
            "ты можешь позвоеить " to "ты можешь позвонить ",
            "ты можешь позвоеить позже " to "ты можешь позвонить позже ",
            "ты можешь позвонить позже " to "ты можешь позвонить позже ")
        repeat(rounds) { round ->
            val pause = if (round % 2 == 0) 50L else 100L
            for ((typed, expected) in cases) {
                fresh()
                val bounds = typed.toSet().associateWith { char -> Rect(if (char == ' ')
                    checkNotNull(driver.device.findObject(By.desc(context.getString(R.string.key_space)))).visibleBounds
                    else driver.characterKey(char.toString()).visibleBounds) }
                val taps = org.json.JSONArray()
                val received = org.json.JSONArray()
                val down = StringBuilder(); val up = StringBuilder()
                var overflow = false
                val keyboard = keyboardSnapshot()
                instrumentation.runOnMainSync {
                    keyboard.keys.forEach { key -> key.setOnTouchListener { view, event ->
                        val label = if (view is io.github.mesteriis.rune.keyboard.ime.ui.SpaceKeyView) " "
                            else (view as? android.widget.TextView)?.text?.toString().orEmpty()
                        if (event.actionMasked == android.view.MotionEvent.ACTION_DOWN) down.append(label)
                        if (event.actionMasked == android.view.MotionEvent.ACTION_UP) up.append(label)
                        if (received.length() >= 512) overflow = true else received.put(org.json.JSONObject().put("key", label).put("edge", event.actionMasked)
                            .put("eventTime", event.eventTime).put("downTime", event.downTime)
                            .put("dispatchTime", SystemClock.uptimeMillis())
                            .put("x", event.rawX).put("y", event.rawY))
                        false
                    } }
                }
                var receivedDown = ""; var receivedUp = ""; var nativeEvents = ""
                try {
                    for (char in typed) {
                        val started = SystemClock.uptimeMillis()
                        touchOwnQaKey(bounds.getValue(char))
                        taps.put(org.json.JSONObject().put("key", char.toString())
                            .put("x", bounds.getValue(char).exactCenterX())
                            .put("y", bounds.getValue(char).exactCenterY())
                            .put("elapsedMs", SystemClock.uptimeMillis() - started))
                        SystemClock.sleep(pause)
                    }
                } finally {
                    instrumentation.runOnMainSync {
                        keyboard.keys.forEach { it.setOnTouchListener(null) }
                        receivedDown = down.toString(); receivedUp = up.toString()
                        nativeEvents = received.toString()
                    }
                    instrumentation.sendStatus(0, Bundle().apply {
                        putInt("forensic_round", round); putLong("pause_ms", pause)
                        putString("requested_taps", taps.toString())
                        putString("received_down", receivedDown); putString("received_up", receivedUp)
                        putString("native_key_events", nativeEvents)
                    })
                }
                assertFalse("Native touch trace exceeded phrase bound", overflow)
                assertEquals("Unexpected native DOWN receivers before correction", typed, receivedDown)
                assertEquals("Unexpected native UP receivers before correction", typed, receivedUp)
                driver.awaitFieldText(field, expected)
                report("input-forensics-$round-$pause", typed, expected, text())
                val correctedLastWord = typed.trimEnd().substringAfterLast(' ') != expected.trimEnd().substringAfterLast(' ')
                // Typing and exact spelling Undo must use Rune-owned context only. Ordinary
                // grapheme deletion outside composition has a separate bounded-read contract.
                noReadback()
                if (correctedLastWord) {
                    driver.tapDelete()
                    driver.awaitFieldText(field, typed.trimEnd())
                    report("undo-forensics-$round-$pause", typed.trimEnd(), typed.trimEnd(), text())
                    noReadback()
                }
            }
        }
    }

    @Test fun reviewedPhraseFixesAtTwoPacesWithExactUndo() {
        val cases = listOf("я прийду " to "я приду ", "спосибо " to "спасибо ",
            "мы скороо " to "мы скоро ")
        for (pause in listOf(50L, 100L)) for ((typed, expected) in cases) {
            fresh()
            val bounds = typed.toSet().associateWith { char -> Rect(if (char == ' ')
                checkNotNull(driver.device.findObject(By.desc(context.getString(R.string.key_space)))).visibleBounds
                else driver.characterKey(char.toString()).visibleBounds) }
            val started = SystemClock.uptimeMillis()
            for (char in typed) {
                touchOwnQaKey(bounds.getValue(char))
                SystemClock.sleep(pause)
            }
            driver.awaitFieldText(field, expected)
            report("reviewed-phrase-$pause", typed, expected, text(), SystemClock.uptimeMillis() - started)
            driver.tapDelete()
            driver.awaitFieldText(field, typed.trimEnd())
            noReadback()
        }
    }

    @Test fun normalTouchTypingChecksCorrectionsAndUnchangedWords() {
        val cases = listOf("ссын" to "сын", "ггня" to "огня", "жкчь" to "жечь", "внтз" to "вниз",
            "зочу" to "хочу", "смотруть" to "смотреть", "заберай" to "забирай", "расмотри" to "рассмотри",
            "надо" to "надо", "мама" to "мама", "конь" to "конь", "нудо" to "нудо",
            "хантера" to "хантера", "ность" to "ность")
        val failures = mutableListOf<String>()
        for ((typed, word) in cases) {
            fresh(); typed.forEach { driver.tapKey(it.toString()) }
            driver.awaitFieldText(field, typed)
            space(); SystemClock.sleep(350)
            val actual = text(); val expected = "$word "
            report("normal", typed, expected, actual)
            if (actual != expected) failures += "$typed: expected=$expected actual=$actual"
            noReadback()
        }
        assertTrue("Real typing mismatches: ${failures.joinToString("; ")}", failures.isEmpty())
    }

    @Test fun knownAmbiguousWordsCanBeCorrectedAndUndone() {
        for ((typed, expected) in listOf("однаео" to "однако", "ччасам" to "часам",
            "седречная" to "сердечная", "кардинаьлно" to "кардинально")) {
            fresh()
            typed.forEach { driver.tapKey(it.toString()) }
            driver.awaitFieldText(field, typed)
            assertNotNull(driver.device.wait(Until.findObject(
                By.desc(context.getString(R.string.candidate_correction, expected))), 5000))
            space()
            driver.awaitFieldText(field, "$expected ")
            driver.tapDelete()
            driver.awaitFieldText(field, typed)
            report("ambiguous-word-undo", typed, typed, text())
            noReadback()
        }
    }

    @Test fun separatelyQualifiedRescueCorrectsAndUndoesPublicWords() {
        for ((typed, expected) in listOf("певарю" to "пекарню", "урокнгь" to "уровень",
            "изгнкп" to "изгнан", "нагооова" to "наготове")) {
            fresh()
            typed.forEach { driver.tapKey(it.toString()) }
            driver.awaitFieldText(field, typed)
            assertNotNull(driver.device.wait(Until.findObject(
                By.desc(context.getString(R.string.candidate_correction, expected))), 5000))
            space(); driver.awaitFieldText(field, "$expected ")
            driver.tapDelete(); driver.awaitFieldText(field, typed)
            report("qualified-rescue-undo", typed, typed, text()); noReadback()
        }
    }

    @Test fun jointDiagnosticExplainsRareProtectionWithoutChangingTheWord() {
        val recorder = io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider
            .create(context) as io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsRecorder
        fun flush() {
            val done = java.util.concurrent.CountDownLatch(1)
            var success = false
            recorder.barrier { success = it; done.countDown() }
            check(done.await(3, java.util.concurrent.TimeUnit.SECONDS) && success)
        }
        flush()
        assumeTrue("Existing metadata diagnostics consent required", recorder.preferences.metadata)
        fun events(): Map<String, Int> {
            flush()
            return (0..3).flatMap { index ->
                val file = java.io.File(context.noBackupFilesDir, "typing-diagnostics/metadata.$index.jsonl")
                if (!file.exists()) emptyList() else {
                    check(file.length() <= 1_048_576)
                    file.readLines()
                }
            }.groupingBy { it }.eachCount()
        }
        fresh(); val before = events()
        "нудо".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(field, "нудо")
        val suggestion = driver.device.wait(Until.findObject(
            By.desc(context.getString(R.string.candidate_correction, "надо"))), 5000)
        assertNotNull(suggestion)
        assertEquals("надо", suggestion!!.text) // A protected original must not show an auto-replace arrow.
        val reasons = events().entries.filter { it.value > (before[it.key] ?: 0) }.map { org.json.JSONObject(it.key) }
            .filter { it.optString("kind") == "RANKING" && it.optString("source") == "JOINT" }
            .map { it.getString("reason") }
        assertTrue("Expected precise rare-word refusal, observed fixed reasons: $reasons", "RARE_ORIGINAL" in reasons)
        space(); driver.awaitFieldText(field, "нудо ")
        assertTrue(events().entries.filter { it.value > (before[it.key] ?: 0) }.map { org.json.JSONObject(it.key) }
            .any { it.optString("kind") == "BOUNDARY" && it.optString("reason") == "RARE_ORIGINAL" })
        report("rare-protection-manual-suggestion", "нудо", "нудо ", text()); noReadback()
    }

    @Test fun correctionPreviewAndUndoPreserveNextWord() {
        fresh(); "ссын".forEach { driver.tapKey(it.toString()) }
        val preview = driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, "сын"))), 5000)
        assertNotNull(preview)
        assertEquals(context.getString(R.string.candidate_auto_preview_label, "сын"), preview!!.text)
        space(); driver.awaitFieldText(field, "сын ")
        "до".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(field, "сын до")
        val undo = driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_undo, "ссын"))), 5000)
        assertNotNull(undo); undo!!.click(); driver.awaitFieldText(field, "ссын до")
        report("visible-undo", "ссын до", "ссын до", text()); noReadback()
        fresh(); "зочу".forEach { driver.tapKey(it.toString()) }; space()
        driver.awaitFieldText(field, "хочу "); driver.tapDelete(); driver.awaitFieldText(field, "зочу")
        report("backspace-undo", "зочу", "зочу", text()); noReadback()
    }

    @Test fun rapidShortWordCorrectionAtThreePacesKeepsFollowingWords() {
        val failures = mutableListOf<String>()
        for (pause in listOf(50L, 100L, 150L)) {
            fresh()
            val typed = "ссын идет домой "
            val bounds = typed.toSet().associateWith { char -> Rect(if (char == ' ')
                checkNotNull(driver.device.findObject(By.desc(context.getString(R.string.key_space)))).visibleBounds
                else driver.characterKey(char.toString()).visibleBounds) }
            val start = SystemClock.uptimeMillis()
            for (char in typed) {
                touchOwnQaKey(bounds.getValue(char))
                SystemClock.sleep(pause)
            }
            val elapsed = SystemClock.uptimeMillis() - start
            SystemClock.sleep(350)
            val actual = text(); val expected = "сын идет домой "
            report("rapid-$pause", typed, expected, actual, elapsed)
            if (actual != expected) failures += "$pause ms: $actual"
            noReadback()
        }
        assertTrue("Rapid typing mismatches: ${failures.joinToString("; ")}", failures.isEmpty())
    }
}

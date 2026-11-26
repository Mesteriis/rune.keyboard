package io.github.mesteriis.rune.keyboard.qa

import android.content.SharedPreferences
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsPreferences
import java.lang.reflect.Proxy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

/** These fakes do not read or write device preferences. */
class PreferenceSnapshotRestoreInstrumentedTest {
    @Test fun ordinaryBoundaryTestsRequireExplicitOptInForActiveDiagnostics() {
        for (metadata in listOf(false, true)) for (text in listOf(false, true)) {
            val preferences = DiagnosticsPreferences(metadata = metadata, text = text)
            requireOrdinaryDiagnosticsSafety(preferences, allowRotation = true)
            if (metadata || text) {
                assertThrows(IllegalStateException::class.java) {
                    requireOrdinaryDiagnosticsSafety(preferences, allowRotation = false)
                }
            } else requireOrdinaryDiagnosticsSafety(preferences, allowRotation = false)
        }
    }

    private fun fake(commit: Boolean, restored: Map<String, *>): SharedPreferences {
        lateinit var editor: SharedPreferences.Editor
        editor = Proxy.newProxyInstance(SharedPreferences.Editor::class.java.classLoader,
            arrayOf(SharedPreferences.Editor::class.java)) { _, method, _ ->
            if (method.name == "commit") commit else editor
        } as SharedPreferences.Editor
        return Proxy.newProxyInstance(SharedPreferences::class.java.classLoader,
            arrayOf(SharedPreferences::class.java)) { _, method, _ ->
            when (method.name) {
                "edit" -> editor
                "getAll" -> restored
                else -> error("Unexpected fake method")
            }
        } as SharedPreferences
    }

    @Test fun unsuccessfulCommitIsRejected() {
        val error = assertThrows(IllegalStateException::class.java) {
            restorePreferenceSnapshot(fake(false, emptyMap<String, Any>()), mapOf("enabled" to true))
        }
        assertEquals("Failed to restore preferences", error.message)
    }

    @Test fun mismatchingRestoredValuesAreRejected() {
        val error = assertThrows(IllegalStateException::class.java) {
            restorePreferenceSnapshot(fake(true, emptyMap<String, Any>()), mapOf("enabled" to true))
        }
        assertEquals("Restored preferences differ from snapshot", error.message)
    }

    @Test fun unsupportedValuesAreRejected() {
        val error = assertThrows(IllegalStateException::class.java) {
            restorePreferenceSnapshot(fake(true, emptyMap<String, Any>()), mapOf("invalid" to setOf(1)))
        }
        assertEquals("Unsupported preference set", error.message)
    }

    @Test fun matchingSnapshotIsAccepted() {
        val snapshot = mapOf("flag" to true, "count" to 2, "wide" to 3L,
            "ratio" to 1.5f, "name" to "value", "list" to setOf("one", "two"))
        restorePreferenceSnapshot(fake(true, snapshot), snapshot)
        assertTrue(snapshot.isNotEmpty())
    }

    @Test fun secureImeSettingsRestoreExactValueAndAbsence() {
        val values = mutableMapOf("enabled_input_methods" to "other/.Ime",
            "show_ime_with_hard_keyboard" to "1")
        val commands = mutableListOf<String>()
        fun shell(command: String): String {
            commands += command
            if (command == "echo rune;sentinel") return "rune;sentinel"
            val parts = command.split(' ')
            val key = parts[3]
            return when (parts[1]) {
                "get" -> values[key] ?: "null"
                "delete" -> { values.remove(key); "" }
                "put" -> { values[key] = parts[4]; "" }
                else -> error("Unexpected fake command")
            }
        }
        val enabled = "first/.Ime;123:second/.Ime;-42"
        restoreSecureImeSetting("enabled_input_methods", enabled, ::shell)
        restoreSecureImeSetting("show_ime_with_hard_keyboard", "null", ::shell)
        assertEquals(enabled, values["enabled_input_methods"])
        assertEquals(null, values["show_ime_with_hard_keyboard"])
        assertTrue(commands.contains("settings put secure enabled_input_methods $enabled"))
        assertTrue(commands.contains("settings delete secure show_ime_with_hard_keyboard"))
    }

    @Test fun secureImeSettingsRejectUnsafeOrUnrestoredValues() {
        val commands = mutableListOf<String>()
        val shell: (String) -> String = { command -> commands += command; "other" }
        assertThrows(IllegalStateException::class.java) {
            restoreSecureImeSetting("enabled_input_methods", "x';danger", shell)
        }
        assertTrue(commands.isEmpty())
        assertThrows(IllegalStateException::class.java) {
            restoreSecureImeSetting("selected_input_method_subtype", "123", shell)
        }
        assertTrue(commands.contains("settings put secure selected_input_method_subtype 123"))
    }

    @Test fun shellInterpretingSeparatorsCannotReceiveSavedImeList() {
        val commands = mutableListOf<String>()
        val shell: (String) -> String = { command ->
            commands += command
            if (command == "echo rune;sentinel") "rune" else "other"
        }
        assertThrows(IllegalStateException::class.java) {
            restoreSecureImeSetting("enabled_input_methods", "first/.Ime;123:second/.Ime", shell)
        }
        assertTrue(commands.none { it.startsWith("settings put") })
    }

    @Test fun deviceShellPreservesSeparatorAsArgument() {
        val driver = ImeTestDriver()
        assertEquals("rune;sentinel", driver.shell("echo rune;sentinel"))
    }
}

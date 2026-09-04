package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.content.res.AssetManager
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.security.MessageDigest

/** Candidate-worker-confined lazy reader for public, content-free canonical spelling assets. */
class AndroidCanonicalCaseLexicon(private val assets: AssetManager) : CanonicalCaseLexicon {
    private val loaded = arrayOfNulls<CanonicalCaseData>(KeyboardLanguage.entries.size)
    private val attempted = BooleanArray(KeyboardLanguage.entries.size)

    override fun lookup(language: KeyboardLanguage, key: String): CanonicalCase? {
        val index = language.ordinal
        if (!attempted[index]) {
            attempted[index] = true
            loaded[index] = try {
                val trusted = FrozenCanonicalCaseLexicons.forLanguage(language)
                val bytes = assets.open(trusted.path, AssetManager.ACCESS_BUFFER).use { it.readBytes() }
                require(bytes.size.toLong() == trusted.bytes && sha256(bytes) == trusted.sha256) { "CASE_HASH" }
                CanonicalCaseData.validate(bytes)
            } catch (_: Exception) {
                null
            }
        }
        return loaded[index]?.lookup(key)
    }

    private fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it) }
}

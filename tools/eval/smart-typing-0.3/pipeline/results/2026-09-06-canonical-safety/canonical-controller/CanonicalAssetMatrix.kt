package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import java.io.File
import java.nio.channels.FileChannel
import java.nio.file.StandardOpenOption
import java.security.MessageDigest
import java.util.Base64

/** Public-fixture asset/API observation only. Does not implement or evaluate a changed policy. */
object CanonicalAssetMatrix {
    @JvmStatic fun main(args: Array<String>) {
        check(args.size == 2)
        val assets = File(args[1])
        fun mapping(file: File) = FileChannel.open(file.toPath(), StandardOpenOption.READ).use {
            it.map(FileChannel.MapMode.READ_ONLY, 0, it.size())
        }
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN, FrozenPackedLexicons.SPANISH).map { trust ->
            val lang = trust.language.locale.language
            val load = PackedLexiconData.validate(trust, mapping(File(assets, "smarttyping/lexicon/$lang.trie")),
                mapping(File(assets, "smarttyping/lexicon/$lang.trie.lengths")),
                mapping(File(assets, "smarttyping/lexicon/frequency/$lang.ranks")))
            check(load is PackedLexiconLoad.Ready)
            load.lexicon
        }
        val cases = KeyboardLanguage.entries.associateWith { language ->
            val trust = FrozenCanonicalCaseLexicons.forLanguage(language)
            val bytes = File(assets, trust.path).readBytes()
            check(bytes.size.toLong() == trust.bytes && MessageDigest.getInstance("SHA-256").digest(bytes)
                .joinToString("") { "%02x".format(it) } == trust.sha256)
            CanonicalCaseData.validate(bytes)
        }
        val lexicon = PackedCandidateLexicon(handles)
        fun encoded(text: String) = Base64.getEncoder().encodeToString(text.toByteArray(Charsets.UTF_8))
        File(args[0]).readLines(Charsets.UTF_8).forEachIndexed { index, token ->
            val key = TokenUnicode.folded(token)
            KeyboardLanguage.entries.forEach { active ->
                val route = LanguageRouter.route(token, active)
                println(listOf("R", index, encoded(token), active.locale.language,
                    route.primary?.locale?.language ?: "NONE", route.fallback?.locale?.language ?: "NONE",
                    route.protectedReason?.name ?: "NONE").joinToString("\t"))
            }
            KeyboardLanguage.entries.forEach { language ->
                val control = CandidateSearchControl(CandidateCancellation { false })
                val exact = lexicon.exact(language, key, control)
                val canonical = cases.getValue(language).lookup(key)
                println(listOf("M", index, encoded(token), language.locale.language, exact.name,
                    canonical?.text?.let(::encoded) ?: "NONE", canonical?.unambiguous ?: "NONE",
                    control.inspectedStates, control.checkpoint()).joinToString("\t"))
            }
        }
        System.err.println("ACTUAL_PACKAGED_ASSET_MATRIX_COMPLETE")
    }
}

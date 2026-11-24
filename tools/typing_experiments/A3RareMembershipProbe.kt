package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import java.io.File
import java.nio.channels.FileChannel
import java.nio.file.StandardOpenOption

/** Aggregate only: no user text or words are emitted. */
object A3RareMembershipProbe {
    @JvmStatic fun main(args: Array<String>) {
        check(args.size == 2)
        val assets = File(args[0]); val words = File(args[1]).readLines()
        check(words.isNotEmpty() && words == words.distinct().sorted())
        fun map(path: String) = FileChannel.open(File(assets, path).toPath(), StandardOpenOption.READ).use {
            it.map(FileChannel.MapMode.READ_ONLY, 0, it.size())
        }
        val trust = FrozenPackedLexicons.RUSSIAN
        val loaded = PackedLexiconData.validate(trust, map("smarttyping/lexicon/ru.trie"),
            map("smarttyping/lexicon/ru.trie.lengths"), map("smarttyping/lexicon/frequency/ru.ranks"))
        check(loaded is PackedLexiconLoad.Ready)
        val dictionary = PackedCandidateLexicon(listOf(loaded.lexicon))
        val morphology = PackedMorphologyLexicon.validate(map(FrozenMorphologyLexicon.ASSET_PATH),
            FrozenMorphologyLexicon.ASSET_SHA256)
        val rare = PackedRareWordLexicon.validate(map(FrozenRareWordLexicon.ASSET_PATH), FrozenRareWordLexicon.ASSET_SHA256)
        var dictionaryPresent = 0; var morphologyPresent = 0; var absentBoth = 0
        for (word in words) {
            check(word.length in 3..4 && word.all { it in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" })
            val d = dictionary.exact(KeyboardLanguage.RUSSIAN, word, CandidateSearchControl(CandidateCancellation { false }))
            val m = morphology.lookup(KeyboardLanguage.RUSSIAN, word)
            val r = rare.lookup(word)
            check(d != ExactMembership.UNAVAILABLE && m.available && r.available && r.present)
            if (d == ExactMembership.PRESENT) dictionaryPresent++
            if (m.present) morphologyPresent++
            if (d == ExactMembership.ABSENT && !m.present) absentBoth++
        }
        println("words=${words.size} dictionaryPresent=$dictionaryPresent morphologyPresent=$morphologyPresent absentBoth=$absentBoth")
    }
}

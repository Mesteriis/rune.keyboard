package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import android.content.res.AssetManager
import android.os.Looper
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidPackedLexiconLoader

/** Worker-only mapping of all feature data; the owner supplies hash-validated model bytes. */
internal object AndroidContextualRankerLoader {
    fun load(assets: AssetManager, modelBytes: ByteArray): ContextualRanker? {
        if (Looper.myLooper() == Looper.getMainLooper() || Thread.currentThread().isInterrupted) return null
        return try {
            fun mapped(name: String, size: Long) = assets.openFd("smarttyping/experiments/$name").use {
                AndroidPackedLexiconLoader.mapDescriptor(it, size)
            }
            val wiki = WordPairFeatures.openPackaged(mapped("ru-wiki.ctx", FrozenContextualAssets.WIKI_BYTES),
                FrozenContextualAssets.WIKI_BYTES) ?: return null
            val conversation = WordPairFeatures.openPackaged(mapped("ru-conversation.ctx", FrozenContextualAssets.CONVERSATION_BYTES),
                FrozenContextualAssets.CONVERSATION_BYTES) ?: return null
            val dictionary = GrammarFeatureDictionary.openPackaged(mapped("ru-context.gram", FrozenContextualAssets.GRAMMAR_BYTES),
                FrozenContextualAssets.GRAMMAR_BYTES) ?: return null
            ContextualRanker.create(modelBytes, wiki, conversation, dictionary)
        } catch (_: Exception) { null }
    }
}

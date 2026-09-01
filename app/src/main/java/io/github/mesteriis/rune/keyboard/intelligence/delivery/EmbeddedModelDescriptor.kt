package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.content.Context
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelManifestParser

object EmbeddedModelDescriptor {
    private const val ASSET_PATH = "model/rune-text-0.1.json"

    fun load(context: Context): ModelDescriptor = context.assets.open(ASSET_PATH).bufferedReader().use { reader ->
        ModelManifestParser.parse(reader.readText())
    }
}

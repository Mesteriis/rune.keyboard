package io.github.mesteriis.rune.keyboard.ime.emoji

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.File

class EmojiCatalogTest {
    @Test fun `all ISO controls line separators and Unicode blank fields are refused`() {
        val controls = (0..0xFFFF).filter { Character.isISOControl(it) }.map { it.toChar() } + listOf('\u2028', '\u2029')
        val rows = fixture.trimEnd('\n').split('\n')
        for (column in 2..5) {
            val fields = rows.last().split('\t').toMutableList()
            for (control in controls) {
                fields[column] = "x${control}y"
                val text = rows.take(2).joinToString("\n", postfix = "\n") + fields.joinToString("\t") + "\n"
                assertThrows(IllegalArgumentException::class.java) { read(text) }
            }
            for (blank in listOf("", " ", "\u00A0", "\u2007", "\u202F", "\u3000")) {
                fields[column] = blank
                val text = rows.take(2).joinToString("\n", postfix = "\n") + fields.joinToString("\t") + "\n"
                assertThrows(IllegalArgumentException::class.java) { read(text) }
            }
        }
    }

    @Test fun `field slot reuse preserves earlier entries and exact surrounding whitespace`() {
        val extra = "E\tpeople\t😀\t second name \t второе имя \t segundo nombre \n"
        val entries = read(fixture + extra).categories.single().entries
        assertEquals(listOf("👩‍💻", "😀"), entries.map { it.glyph })
        assertEquals("woman technologist", entries.first().names.english)
        assertEquals(" second name ", entries.last().names.english)
        assertEquals(" второе имя ", entries.last().names.russian)
        assertEquals(" segundo nombre ", entries.last().names.spanish)
    }

    private val asset = File("src/main/assets/emoji/catalog-v1.tsv")
    private fun read(text: String) = EmojiCatalog.read(text.byteInputStream())
    private val fixture = "# rune-emoji-catalog-v1\n" +
        "G\tpeople\t👋\tPeople\tЛюди\tPersonas\n" +
        "E\tpeople\t👩‍💻\twoman technologist\tженщина-программист\ttecnóloga\n"

    @Test fun `packaged catalog retains every group and localized label`() {
        val catalog = EmojiCatalog.read(asset.inputStream())
        assertEquals(listOf("smileys", "people", "animals", "food", "travel", "activities", "objects", "symbols", "flags"),
            catalog.categories.map { it.id })
        assertEquals(listOf(168, 385, 153, 135, 218, 85, 262, 223, 269), catalog.categories.map { it.entries.size })
        val first = catalog.categories.first().entries.first()
        assertEquals("😀", first.glyph)
        assertEquals("grinning face", first.names.inLanguage(KeyboardLanguage.ENGLISH))
        assertEquals("широко улыбается", first.names.inLanguage(KeyboardLanguage.RUSSIAN))
        assertEquals("cara sonriendo", first.names.inLanguage(KeyboardLanguage.SPANISH))
        assertEquals("Смайлы и эмоции", catalog.categories.first().names.inLanguage(KeyboardLanguage.RUSSIAN))
        // An independent line/split reference checks every persisted field and source order.
        val groups = catalog.categories.map { listOf("G", it.id, it.icon, it.names.english, it.names.russian, it.names.spanish).joinToString("\t") }
        val rows = catalog.categories.flatMap { category -> category.entries.map {
            listOf("E", category.id, it.glyph, it.names.english, it.names.russian, it.names.spanish).joinToString("\t")
        } }
        assertEquals(asset.readLines().drop(1), groups + rows)
    }

    @Test fun `sequence bytes preserve joiners flags selectors keycaps and tag sequences`() {
        val entries = EmojiCatalog.read(asset.inputStream()).categories.flatMap { it.entries }
        listOf("👩‍💻", "🇪🇸", "❤️", "1️⃣", "🏴\uDB40\uDC67\uDB40\uDC62\uDB40\uDC65\uDB40\uDC6E\uDB40\uDC67\uDB40\uDC7F").forEach { expected ->
            assertArrayEquals(expected.toByteArray(), entries.single { it.glyph == expected }.glyph.toByteArray())
        }
    }

    @Test fun `schema row and localization failures never return partial catalog`() {
        listOf(
            fixture.replace("catalog-v1", "catalog-v2"),
            fixture.dropLast(1),
            fixture.replace("E\t", "X\t"),
            fixture.replace("E\tpeople", "E\tunknown"),
            fixture.replace("\tPersonas", "\t"),
            fixture.replace("\ttecnóloga", "\t "),
            fixture.replace("People", "Peo\rple"),
            fixture.replace("People", "Peo\u2028ple"),
            fixture + "\n",
            fixture + "G\tlate\t😀\tLate\tПоздно\tTarde\n",
            fixture + fixture.lines()[2] + "\n",
            fixture.replace("E\tpeople", "E\tPeople"),
            "# rune-emoji-catalog-v1\n",
            fixture.lines().take(2).joinToString("\n", postfix = "\n"),
            fixture.replace("E\tpeople", "G\tpeople"),
        ).forEach { invalid -> assertThrows(IllegalArgumentException::class.java) { read(invalid) } }
    }

    @Test fun `malformed UTF8 is refused and input closed`() {
        var closed = false
        val input = object : ByteArrayInputStream(byteArrayOf(0xC3.toByte(), 0x28)) {
            override fun close() { closed = true; super.close() }
        }
        assertThrows(java.nio.charset.CharacterCodingException::class.java) { EmojiCatalog.read(input) }
        assertTrue(closed)
    }

    @Test fun `oversized input is bounded and closed`() {
        var closed = false
        val input = object : ByteArrayInputStream(ByteArray(1_000_000) { 65 }) {
            override fun close() { closed = true; super.close() }
        }
        assertThrows(IllegalArgumentException::class.java) { EmojiCatalog.read(input) }
        assertTrue(closed)
        assertTrue(input.available() > 0)
    }

    @Test fun `valid input is closed`() {
        var closed = false
        val input = object : ByteArrayInputStream(fixture.toByteArray()) {
            override fun close() { closed = true; super.close() }
        }
        EmojiCatalog.read(input)
        assertTrue(closed)
    }

    @Test fun `palette construction and recents access do not load catalog or check fonts`() {
        var loads = 0
        var probes = 0
        val palette = EmojiPalette({ loads++; read(fixture) }, { probes++; true })
        assertTrue(palette.recents.isEmpty())
        assertEquals(0, loads)
        assertEquals(0, probes)
        assertEquals(1, palette.categories.size)
        assertEquals(1, loads)
        assertEquals(0, probes)
    }

    @Test fun `font probes are limited to opened category and cache supported and unsupported`() {
        var loads = 0
        val probes = mutableListOf<String>()
        val palette = EmojiPalette({ loads++; EmojiCatalog.read(asset.inputStream()) }, { probes.add(it); it == "😀" })
        assertEquals(listOf("😀"), palette.entries("smileys").map { it.glyph })
        assertEquals(168, probes.size)
        assertEquals(1, loads)
        palette.entries("smileys")
        palette.entries("missing")
        assertEquals(168, probes.size)
        assertTrue(palette.entries("food").isEmpty())
        assertEquals(168 + 135, probes.size)
        assertEquals(probes.size, probes.toSet().size)
    }

    @Test fun `recents are bounded deduplicated and owned by one palette`() {
        val catalog = EmojiCatalog.read(asset.inputStream())
        val palette = EmojiPalette({ catalog }, { true })
        val entries = catalog.categories.first().entries.take(40)
        entries.forEach { palette.recordCommitted(it.glyph) }
        assertEquals(entries.takeLast(32).reversed(), palette.recents)
        val snapshot = palette.recents
        palette.recordCommitted(entries[20].glyph)
        assertEquals(entries[20], palette.recents.first())
        assertEquals(32, palette.recents.size)
        assertEquals(32, palette.recents.map { it.glyph }.toSet().size)
        assertEquals(entries.takeLast(32).reversed(), snapshot)
        palette.recordCommitted("not an emoji")
        assertEquals(32, palette.recents.size)
        assertTrue(EmojiPalette({ catalog }, { true }).recents.isEmpty())
    }
}

package io.github.mesteriis.rune.keyboard.intelligence.model

import java.net.URI

class ManifestValidationException(message: String) : IllegalArgumentException(message)

object ModelManifestParser {
    private val requiredKeys = setOf(
        "schemaVersion", "modelId", "version", "displayName", "fileName", "url", "sha256",
        "sizeBytes", "runtimeApi", "minimumRuneVersionCode", "ggufVersion", "architecture", "fileType",
    )
    private val identifier = Regex("[a-z0-9][a-z0-9._-]{0,62}")
    private val version = Regex("[0-9]+\\.[0-9]+\\.[0-9]+(?:-[a-z0-9.-]+)?")
    private val sha256 = Regex("[0-9a-f]{64}")
    private val fileName = Regex("[a-z0-9][a-z0-9._-]{0,126}\\.gguf")

    fun parse(json: String): ModelDescriptor {
        val fields = FlatJsonObjectParser(json).parse()
        if (fields.keys != requiredKeys) {
            val missing = requiredKeys - fields.keys
            val unknown = fields.keys - requiredKeys
            invalid("manifest keys differ; missing=$missing unknown=$unknown")
        }
        if (fields.long("schemaVersion") != 1L) invalid("schemaVersion must be 1")
        val id = fields.string("modelId").checked(identifier, "modelId")
        val modelVersion = fields.string("version").checked(version, "version")
        val name = fields.string("displayName")
        if (name.isBlank() || name.length > 80 || name.any(Char::isISOControl)) invalid("invalid displayName")
        val artifactName = fields.string("fileName").checked(fileName, "fileName")
        val url = fields.string("url")
        validateUrl(url, artifactName)
        val digest = fields.string("sha256")
        if (!sha256.matches(digest)) invalid("invalid sha256")
        val size = fields.long("sizeBytes")
        if (size <= 0) invalid("sizeBytes must be positive")
        if (fields.long("runtimeApi") != 1L) invalid("runtimeApi must be 1")
        if (fields.long("minimumRuneVersionCode") != 2L) invalid("minimumRuneVersionCode must be 2")
        if (fields.long("ggufVersion") != 3L) invalid("ggufVersion must be 3")
        val architecture = fields.string("architecture")
        if (architecture != "qwen3") invalid("architecture must be qwen3")
        if (fields.long("fileType") != 15L) invalid("fileType must be 15")
        return ModelDescriptor(
            id, modelVersion, name, artifactName, url, digest, size, 1, 2, 3, architecture, 15,
        )
    }

    fun encode(descriptor: ModelDescriptor): String = buildString {
        append('{')
        append("\"schemaVersion\":1,")
        append("\"modelId\":\"").append(escaped(descriptor.id)).append("\",")
        append("\"version\":\"").append(escaped(descriptor.version)).append("\",")
        append("\"displayName\":\"").append(escaped(descriptor.displayName)).append("\",")
        append("\"fileName\":\"").append(escaped(descriptor.fileName)).append("\",")
        append("\"url\":\"").append(escaped(descriptor.downloadUrl)).append("\",")
        append("\"sha256\":\"").append(escaped(descriptor.sha256)).append("\",")
        append("\"sizeBytes\":").append(descriptor.sizeBytes).append(',')
        append("\"runtimeApi\":").append(descriptor.runtimeApi).append(',')
        append("\"minimumRuneVersionCode\":").append(descriptor.minimumRuneVersionCode).append(',')
        append("\"ggufVersion\":").append(descriptor.ggufVersion).append(',')
        append("\"architecture\":\"").append(escaped(descriptor.architecture)).append("\",")
        append("\"fileType\":").append(descriptor.fileType)
        append('}')
    }.also(::parse)

    private fun escaped(value: String): String = buildString {
        value.forEach { char ->
            when (char) {
                '\\' -> append("\\\\")
                '"' -> append("\\\"")
                '\b' -> append("\\b")
                '\u000c' -> append("\\f")
                '\n' -> append("\\n")
                '\r' -> append("\\r")
                '\t' -> append("\\t")
                else -> if (char < ' ') append("\\u%04x".format(char.code)) else append(char)
            }
        }
    }

    private fun validateUrl(value: String, artifactName: String) {
        val uri = try { URI(value) } catch (_: Exception) { invalid("invalid url") }
        if (uri.scheme != "https" || uri.host != "github.com" || uri.port != -1 || uri.userInfo != null ||
            uri.query != null || uri.fragment != null
        ) invalid("url must be an HTTPS GitHub Release URL")
        val parts = uri.path.split('/').filter(String::isNotEmpty)
        if (parts.size != 6 || parts[0] != "Mesteriis" || parts[1] != "rune.keyboard" ||
            parts[2] != "releases" || parts[3] != "download" || parts[5] != artifactName ||
            !identifier.matches(parts[4])
        ) invalid("url must target the immutable Rune model release asset")
    }

    private fun String.checked(pattern: Regex, field: String): String =
        also { if (!pattern.matches(it)) invalid("invalid $field") }

    private fun Map<String, JsonPrimitive>.string(key: String): String =
        (get(key) as? JsonPrimitive.Text)?.value ?: invalid("$key must be a string")

    private fun Map<String, JsonPrimitive>.long(key: String): Long =
        (get(key) as? JsonPrimitive.Integer)?.value ?: invalid("$key must be an integer")

    private fun invalid(message: String): Nothing = throw ManifestValidationException(message)
}

private sealed interface JsonPrimitive {
    data class Text(val value: String) : JsonPrimitive
    data class Integer(val value: Long) : JsonPrimitive
    data class Bool(val value: Boolean) : JsonPrimitive
    data object Null : JsonPrimitive
}

private class FlatJsonObjectParser(private val source: String) {
    private var index = 0

    fun parse(): Map<String, JsonPrimitive> {
        whitespace(); expect('{'); whitespace()
        val result = linkedMapOf<String, JsonPrimitive>()
        if (take('}')) return finish(result)
        while (true) {
            val key = string(); whitespace(); expect(':'); whitespace()
            if (result.put(key, primitive()) != null) fail("duplicate key: $key")
            whitespace()
            if (take('}')) return finish(result)
            expect(','); whitespace()
        }
    }

    private fun finish(result: Map<String, JsonPrimitive>): Map<String, JsonPrimitive> {
        whitespace(); if (index != source.length) fail("trailing content"); return result
    }

    private fun primitive(): JsonPrimitive = when (peek()) {
        '"' -> JsonPrimitive.Text(string())
        '-', in '0'..'9' -> JsonPrimitive.Integer(integer())
        't' -> { literal("true"); JsonPrimitive.Bool(true) }
        'f' -> { literal("false"); JsonPrimitive.Bool(false) }
        'n' -> { literal("null"); JsonPrimitive.Null }
        else -> fail("unsupported JSON value")
    }

    private fun string(): String {
        expect('"'); val result = StringBuilder()
        while (index < source.length) {
            when (val char = source[index++]) {
                '"' -> return result.toString()
                '\\' -> {
                    if (index >= source.length) fail("truncated escape")
                    result.append(when (val escaped = source[index++]) {
                        '"', '\\', '/' -> escaped
                        'b' -> '\b'; 'f' -> '\u000c'; 'n' -> '\n'; 'r' -> '\r'; 't' -> '\t'
                        'u' -> unicodeEscape()
                        else -> fail("invalid escape")
                    })
                }
                else -> { if (char < ' ') fail("control character in string"); result.append(char) }
            }
        }
        fail("unterminated string")
    }

    private fun unicodeEscape(): Char {
        if (index + 4 > source.length) fail("truncated unicode escape")
        return source.substring(index, index + 4).toIntOrNull(16)?.toChar()
            ?.also { index += 4 } ?: fail("invalid unicode escape")
    }

    private fun integer(): Long {
        val start = index
        if (take('-') && index == source.length) fail("invalid number")
        if (take('0')) {
            if (peek() in '0'..'9') fail("leading zero")
        } else {
            if (peek() !in '1'..'9') fail("invalid number")
            while (peek() in '0'..'9') index++
        }
        if (peek() == '.' || peek() == 'e' || peek() == 'E') fail("integer required")
        return source.substring(start, index).toLongOrNull() ?: fail("integer overflow")
    }

    private fun literal(value: String) {
        if (!source.startsWith(value, index)) fail("invalid literal")
        index += value.length
    }

    private fun whitespace() { while (peek()?.isWhitespace() == true) index++ }
    private fun expect(char: Char) { if (!take(char)) fail("expected $char") }
    private fun take(char: Char): Boolean = if (peek() == char) { index++; true } else false
    private fun peek(): Char? = source.getOrNull(index)
    private fun fail(message: String): Nothing = throw ManifestValidationException("$message at $index")
}

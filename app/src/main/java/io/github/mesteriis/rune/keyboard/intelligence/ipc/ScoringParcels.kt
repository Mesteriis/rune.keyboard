package io.github.mesteriis.rune.keyboard.intelligence.ipc

import android.os.BadParcelableException
import android.os.Parcel
import android.os.Parcelable

/** Custom scalar wire prevents Parcel.createTypedArrayList/readString unbounded allocations. */
class ScoreRequestParcel(val value: ScoringInput) : Parcelable {
    override fun describeContents() = 0
    override fun writeToParcel(out: Parcel, flags: Int) {
        writeToken(out, value.token)
        writeWireText(out, value.prefix)
        value.continuations.forEach { writeWireText(out, it) }
    }
    companion object {
        @JvmField val CREATOR = object : Parcelable.Creator<ScoreRequestParcel> {
            override fun createFromParcel(input: Parcel) = checked {
                val token = readToken(input)
                ScoreRequestParcel(ScoringInput(token, readText(input, 4096),
                    List(token.candidateIds.size) { readText(input, 512) }))
            }
            override fun newArray(size: Int): Array<ScoreRequestParcel?> {
                require(size in 0..8); return arrayOfNulls(size)
            }
        }
    }
}
class ScoreReplyParcel(val value: ScoringReply) : Parcelable {
    override fun describeContents() = 0
    override fun writeToParcel(out: Parcel, flags: Int) {
        writeToken(out, value.token); out.writeInt(value.code); out.writeLong(value.elapsedMillis)
        out.writeInt(value.scores.size)
        value.scores.forEach { out.writeInt(it.candidateId); out.writeDouble(it.sumLogProbability); out.writeInt(it.tokenCount) }
    }
    companion object {
        @JvmField val CREATOR = object : Parcelable.Creator<ScoreReplyParcel> {
            override fun createFromParcel(input: Parcel) = checked {
                val token = readToken(input); require(input.dataAvail() >= 16)
                val code = input.readInt(); val elapsed = input.readLong()
                val count = bounded(input.readInt(), 0, 8)
                require(input.dataAvail() >= count * 16)
                ScoreReplyParcel(ScoringReply(token, code, elapsed,
                    List(count) { NumericScore(input.readInt(), input.readDouble(), input.readInt()) }))
            }
            override fun newArray(size: Int): Array<ScoreReplyParcel?> {
                require(size in 0..8); return arrayOfNulls(size)
            }
        }
    }
}
private fun writeToken(out: Parcel, token: ScoringToken) {
    out.writeInt(1); out.writeLong(token.sessionId); out.writeLong(token.revision); out.writeLong(token.requestId)
    out.writeInt(token.candidateIds.size); token.candidateIds.forEach(out::writeInt)
}
private fun readToken(input: Parcel): ScoringToken {
    require(input.dataAvail() >= 32)
    require(input.readInt() == 1)
    val session = input.readLong(); val revision = input.readLong(); val request = input.readLong()
    val count = bounded(input.readInt(), 1, 8)
    require(input.dataAvail() >= count * 4)
    return ScoringToken(session, revision, request, List(count) { input.readInt() })
}
private fun writeWireText(out: Parcel, text: String) {
    out.writeInt(text.length); text.forEach { out.writeInt(it.code) }
}
private fun readText(input: Parcel, maximum: Int): String {
    require(input.dataAvail() >= 4)
    val count = bounded(input.readInt(), 0, maximum)
    require(input.dataAvail() >= count * 4)
    return String(CharArray(count) { bounded(input.readInt(), 0, 65535).toChar() })
}
private fun bounded(value: Int, minimum: Int, maximum: Int): Int {
    require(value in minimum..maximum); return value
}
private inline fun <T> checked(block: () -> T): T = try { block() }
catch (_: IllegalArgumentException) { throw BadParcelableException("invalid scoring wire") }

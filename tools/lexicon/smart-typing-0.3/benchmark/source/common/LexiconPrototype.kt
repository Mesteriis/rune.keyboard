import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.channels.FileChannel
import java.text.Normalizer
import java.util.Locale
import kotlin.math.abs
import kotlin.math.min

private const val MAX_STATES = 8192
private const val MAX_VERIFIED = 64
fun points(s: String): IntArray = s.codePoints().toArray()
fun text(p: IntArray): String = String(p, 0, p.size)
fun canonical(s: String): String = Normalizer.normalize(s.lowercase(Locale.ROOT), Normalizer.Form.NFC)
class BadAsset(message: String): IllegalArgumentException(message)
fun requireAsset(ok: Boolean) { if (!ok) throw BadAsset("Invalid lexicon asset") }
fun mapped(file: File): ByteBuffer {
    requireAsset(file.length() in 16..Int.MAX_VALUE.toLong())
    return RandomAccessFile(file, "r").use { it.channel.map(FileChannel.MapMode.READ_ONLY, 0, it.length()).order(ByteOrder.LITTLE_ENDIAN) }
}
class Front(file: File) {
    val b = mapped(file)
    val count = b.getInt(4)
    private val blocks = b.getInt(12)
    private val data: Int
    init {
        requireAsset(b.getInt(0)==0x31434652 && count>0 && count<=10_000_000 && b.getInt(8)==16 && blocks==(count+15)/16)
        data=16+blocks*4; requireAsset(data<=b.limit())
        var prev=-1
        for(i in 0 until blocks) { val o=b.getInt(16+4*i); requireAsset(o>=0 && o>prev && data.toLong()+o<b.limit());prev=o }
    }
    fun word(id: Int): String {
        requireAsset(id in 0 until count)
        var pos=data+b.getInt(16+(id/16)*4);var previous=ByteArray(0)
        for(i in 0..id%16) {
            requireAsset(pos+2<=b.limit());val prefix=b.get(pos++).toInt() and 255;val suffix=b.get(pos++).toInt() and 255
            requireAsset(prefix<=previous.size && (i!=0 || prefix==0) && prefix+suffix<=128 && pos.toLong()+suffix<=b.limit())
            val current=previous.copyOf(prefix+suffix);for(j in 0 until suffix)current[prefix+j]=b.get(pos+j)
            previous=current;pos+=suffix
        }
        val result=previous.toString(Charsets.UTF_8)
        requireAsset(!result.contains('\uFFFD') && points(result).size in 1..32)
        return result
    }
    fun exact(s: String): Boolean {
        var lo=0;var hi=count
        while(lo<hi) {val mid=(lo+hi) ushr 1;val cmp=comparePoints(points(word(mid)),points(s));if(cmp<0)lo=mid+1 else hi=mid}
        return lo<count && word(lo)==s
    }
}
fun comparePoints(a: IntArray,b: IntArray): Int { for(i in 0 until min(a.size,b.size))if(a[i]!=b[i])return a[i].compareTo(b[i]);return a.size.compareTo(b.size) }
/** Absolute terminal-word length bounds, built offline from the full dictionary. */
class LengthBounds(file: File) {
    private val bytes = mapped(file)
    val mode = bytes.getInt(4)
    val count = bytes.getInt(8)
    private val base = bytes.getInt(12)

    init {
        requireAsset(bytes.getInt(0) == 0x314e454c && count > 0)
        when (mode) {
            1 -> requireAsset(base == 0 && bytes.limit().toLong() == 16L + count * 2L)
            2 -> requireAsset(base >= count && base > 0 && base and (base - 1) == 0 && bytes.limit().toLong() == 16L + base * 4L)
            else -> throw BadAsset("Unknown length metadata")
        }
    }

    private fun minimum(node: Int) = bytes.get(16 + node * 2).toInt() and 255
    private fun maximum(node: Int) = bytes.get(17 + node * 2).toInt() and 255

    fun node(node: Int): Int {
        requireAsset(mode == 1 && node in 0 until count)
        val low = minimum(node)
        val high = maximum(node)
        requireAsset(low in 1..32 && high in low..32)
        return (low shl 8) or high
    }

    fun interval(start: Int, end: Int): Int {
        requireAsset(mode == 2 && start >= 0 && end <= count && start < end)
        var left = start + base
        var right = end + base
        var low = 33
        var high = 0
        while (left < right) {
            if (left and 1 != 0) {
                low = min(low, minimum(left))
                high = maxOf(high, maximum(left))
                left++
            }
            if (right and 1 != 0) {
                right--
                low = min(low, minimum(right))
                high = maxOf(high, maximum(right))
            }
            left = left ushr 1
            right = right ushr 1
        }
        requireAsset(low in 1..32 && high in low..32)
        return (low shl 8) or high
    }
}

interface PrefixIndex {
    fun children(node: Long, depth: Int): List<Pair<Int,Long>>
    fun terminal(node: Long, depth: Int): Boolean
    fun exact(s: String): Boolean
    fun root(): Long
    fun lengthRange(node: Long, depth: Int): Int = 0x0120
}
class SortedIndex(val front: Front, private val lengths: LengthBounds? = null): PrefixIndex {
    init { if (lengths != null) requireAsset(lengths.mode == 2 && lengths.count == front.count) }
    override fun lengthRange(node: Long, depth: Int): Int = lengths?.interval(low(node), high(node)) ?: 0x0120
    private fun low(n: Long)= (n ushr 32).toInt()
    private fun high(n: Long)=n.toInt()
    private fun pair(l: Int,h: Int)=(l.toLong() shl 32) or h.toLong()
    override fun root()=pair(0,front.count)
    override fun exact(s: String)=front.exact(s)
    override fun terminal(node: Long,depth: Int)=low(node)<high(node) && points(front.word(low(node))).size==depth
    override fun children(node: Long,depth: Int): List<Pair<Int,Long>> {
        val out=ArrayList<Pair<Int,Long>>();var lo=low(node);val end=high(node)
        if(terminal(node,depth))lo++
        while(lo<end) {
            val cp=points(front.word(lo))[depth];var l=lo+1;var h=end
            while(l<h) { val m=(l+h) ushr 1;val p=points(front.word(m));if(p.size>depth && p[depth]==cp)l=m+1 else h=m }
            out.add(cp to pair(lo,l));lo=l
        };return out
    }
}
class PackedTrie(file: File, private val lengths: LengthBounds? = null): PrefixIndex {
    val b=mapped(file);private val count=b.getInt(4);private val nodes=b.getInt(8)
    init { requireAsset(b.getInt(0)==0x31525452 && count>0 && nodes>0 && b.getInt(12)==16 && 16L+nodes.toLong()*16==b.limit().toLong()) }
    init { if (lengths != null) requireAsset(lengths.mode == 1 && lengths.count == nodes) }
    override fun lengthRange(node: Long, depth: Int): Int = lengths?.node(node.toInt()) ?: 0x0120
    private fun field(n: Int,field: Int): Int {requireAsset(n in 0 until nodes);return b.getInt(16+n*16+field*4)}
    override fun root()=0L
    override fun terminal(node: Long,depth: Int): Boolean {val t=field(node.toInt(),3);requireAsset(t in 0..count);return t>0}
    override fun children(node: Long,depth: Int): List<Pair<Int,Long>> {
        val out=ArrayList<Pair<Int,Long>>();var n=field(node.toInt(),1);var prev=0
        while(n!=0) {requireAsset(n in 1 until nodes && n>node.toInt() && out.size<256);val c=field(n,0);requireAsset(c in 1..0x10ffff && c !in 0xd800..0xdfff && c>prev);out.add(c to n.toLong());prev=c;n=field(n,2)}
        return out
    }
    override fun exact(s: String): Boolean {var n=0L;for((i,c) in points(s).withIndex()){n=children(n,i).firstOrNull{it.first==c}?.second ?: return false};return terminal(n,points(s).size)}
}
/** True unrestricted DL. Rows include an infinity sentinel; last occurrence state is path-local. */
fun distance(a: IntArray,b: IntArray): Int {
    val inf=a.size+b.size;val h=Array(a.size+2){IntArray(b.size+2)};h[0][0]=inf
    for(i in 0..a.size){h[i+1][0]=inf;h[i+1][1]=i}
    for(j in 0..b.size){h[0][j+1]=inf;h[1][j+1]=j}
    val last=HashMap<Int,Int>()
    for(i in 1..a.size){var db=0;for(j in 1..b.size){val i1=last[b[j-1]] ?: 0;val j1=db;var cost=1;if(a[i-1]==b[j-1]){cost=0;db=j};h[i+1][j+1]=minOf(h[i][j]+cost,h[i+1][j]+1,h[i][j+1]+1,h[i1][j1]+i-i1-1+1+j-j1-1)};last[a[i-1]]=i}
    return h[a.size+1][b.size+1]
}
data class Search(
    val alternatives: List<String>,
    val states: Int,
    val verified: Int,
    val exhausted: Boolean,
    val eligible: Boolean = true,
    val exhaustionReason: String = if (exhausted) "UNSPECIFIED" else "NONE",
    val lengthPruned: Int = 0,
    val evaluatedRows: Int = 0,
    val multisetPruned: Int = 0,
) {
    val prohibitsAutoReplace: Boolean get() = exhausted || !eligible
}

fun eligible(q: String): Boolean {
    val cp=points(q);if(cp.size !in 1..32 || cp.any{!Character.isLetter(it)})return false
    return cp.map{Character.UnicodeScript.of(it)}.toSet().size==1
}
fun trieSearch(
    index: PrefixIndex,
    raw: String,
    bounded: Boolean = true,
    useLengthPruning: Boolean = false,
): Search {
    val query = canonical(raw)
    val points = points(query)
    if (!eligible(query)) return Search(emptyList(), 0, 0, false, false)
    val radius = if (points.size < 5) 1 else 2
    val history = Array(34) { IntArray(points.size + 2) { 1000 } }
    for (j in 0..points.size) history[1][j + 1] = j
    val path = IntArray(32)
    val lastOccurrence = HashMap<Int, Int>()
    val found = ArrayList<String>()
    var states = 0
    var verified = 0
    var evaluatedRows = 0
    var lengthPruned = 0
    var exhaustionReason = "NONE"

    fun visit(node: Long, depth: Int) {
        if (exhaustionReason != "NONE" || depth >= 32) return
        for ((codepoint, next) in index.children(node, depth)) {
            if (bounded && states >= MAX_STATES) {
                exhaustionReason = "STATES"
                return
            }
            // A inspected/pruned child still consumes one visited state. No
            // accounting change is used to make the 8192 cap look easier.
            states++
            if (useLengthPruning) {
                val range = index.lengthRange(next, depth + 1)
                val shortest = range ushr 8
                val longest = range and 255
                if (shortest > points.size + radius || longest < points.size - radius) {
                    lengthPruned++
                    continue
                }
            }
            evaluatedRows++
            val i = depth + 1
            history[i + 1].fill(1000)
            history[i + 1][1] = i
            var matchedColumn = 0
            var rowMinimum = i
            for (j in 1..points.size) {
                val previousRow = lastOccurrence[points[j - 1]] ?: 0
                val previousColumn = matchedColumn
                var cost = 1
                if (codepoint == points[j - 1]) {
                    cost = 0
                    matchedColumn = j
                }
                val value = minOf(
                    history[i][j] + cost,
                    history[i + 1][j] + 1,
                    history[i][j + 1] + 1,
                    history[previousRow][previousColumn] + i - previousRow + j - previousColumn - 1,
                )
                history[i + 1][j + 1] = value
                rowMinimum = min(rowMinimum, value)
            }
            path[depth] = codepoint
            if (rowMinimum > radius) continue
            if (index.terminal(next, i) && history[i + 1][points.size + 1] <= radius) {
                val word = text(path.copyOf(i))
                if (word != query) {
                    if (bounded && verified >= MAX_VERIFIED) {
                        exhaustionReason = "VERIFIED"
                        return
                    }
                    verified++
                    found.add(word)
                }
            }
            val previous = lastOccurrence.put(codepoint, i)
            visit(next, i)
            if (previous == null) lastOccurrence.remove(codepoint) else lastOccurrence[codepoint] = previous
            if (exhaustionReason != "NONE") return
        }
    }
    visit(index.root(), 0)
    return Search(found, states, verified, exhaustionReason != "NONE", true, exhaustionReason, lengthPruned, evaluatedRows)
}

/** A sound edit-distance lower bound: transpositions preserve character counts. */
class MultisetFilter(query: IntArray) {
    private val symbols = query.distinct().sorted().toIntArray()
    private val counts = IntArray(symbols.size)
    private val remaining = IntArray(symbols.size)
    private val querySize = query.size
    init { for (cp in query) counts[symbols.binarySearch(cp)]++ }
    fun permits(word: IntArray, radius: Int): Boolean {
        counts.copyInto(remaining)
        var extra = 0
        for (cp in word) {
            val index = symbols.binarySearch(cp)
            if (index < 0 || remaining[index] == 0) extra++ else remaining[index]--
            if (extra > radius) return false
        }
        return querySize - word.size + extra <= radius
    }
}

class DeleteIndex(file: File,val front: Front) {
    val b=mapped(file);private val records=(b.limit()-16)/24
    init {requireAsset(b.getInt(0)==0x314c4452 && b.getInt(4)==front.count && b.getInt(8)==4 && b.getInt(12)==24 && (b.limit()-16)%24==0)}
    private fun cmp(id: Int,key: IntArray): Int {for(j in 0..3){val cp=b.getInt(16+id*24+4*j);if(cp!=key[j])return cp.compareTo(key[j])};return 0}
    fun search(raw: String, bounded: Boolean = true, usePruning: Boolean = false): Search {
        val query = canonical(raw)
        val queryPoints = points(query)
        if (!eligible(query)) return Search(emptyList(), 0, 0, false, false)
        val radius = if (queryPoints.size < 5) 1 else 2
        val prefix = queryPoints.take(4)
        val keys = sortedSetOf<List<Int>>(Comparator { a, c -> comparePoints(a.toIntArray(), c.toIntArray()) })
        keys.add(prefix)
        var level = setOf(prefix)
        repeat(radius) {
            val next = HashSet<List<Int>>()
            for (key in level) for (j in key.indices) {
                val deletion = key.filterIndexed { index, _ -> index != j }
                keys.add(deletion)
                next.add(deletion)
            }
            level = next
        }
        var states = 0
        var verified = 0
        var multisetPruned = 0
        var lengthPruned = 0
        var exhaustionReason = "NONE"
        val seen = HashSet<Int>()
        val found = ArrayList<String>()
        val multiset = MultisetFilter(queryPoints)
        outer@ for (deletion in keys) {
            val key = deletion.toIntArray().copyOf(4)
            var low = 0
            var high = records
            val minimumLength = maxOf(1, queryPoints.size - radius)
            val maximumLength = min(32, queryPoints.size + radius)
            // Records are already ordered by (key, full-word length, ordinal).
            // The same absolute-length condition used by prefix readers can
            // skip incompatible posting blocks with a lower-bound lookup.
            while (low < high) {
                val middle = (low + high) ushr 1
                val comparison = cmp(middle, key)
                val shorter = usePruning && comparison == 0 && b.getInt(16 + middle * 24 + 16) < minimumLength
                if (comparison < 0 || shorter) low = middle + 1 else high = middle
            }
            while (low < records && cmp(low, key) == 0) {
                val length = b.getInt(16 + low * 24 + 16)
                if (usePruning && length > maximumLength) break
                if (bounded && states >= MAX_STATES) {
                    exhaustionReason = "STATES"
                    break@outer
                }
                states++
                val id = b.getInt(16 + low * 24 + 20)
                requireAsset(length in 1..32 && id in 0 until front.count)
                low++
                if (abs(length - queryPoints.size) > radius) { lengthPruned++; continue }
                if (!seen.add(id)) continue
                val word = front.word(id)
                if (word == query) continue
                val wordPoints = points(word)
                if (usePruning && !multiset.permits(wordPoints, radius)) { multisetPruned++; continue }
                if (bounded && verified >= MAX_VERIFIED) {
                    exhaustionReason = "VERIFIED"
                    break@outer
                }
                verified++
                if (distance(wordPoints, queryPoints) <= radius) found.add(word)
            }
        }
        return Search(found, states, verified, exhaustionReason != "NONE", true, exhaustionReason, lengthPruned, 0, multisetPruned)
    }
}
fun frequency(file: File): Map<String,Int> = file.useLines { lines -> lines.drop(1).associate {val p=it.split('\t');p[0] to p[1].toInt()} }
fun adjacencyPenalty(q: IntArray,w: IntArray,lang: String): Int {
    val rows=if(lang=="ru")listOf("йцукенгшщзхъ","фывапролджэ","ячсмитьбю") else listOf("qwertyuiop","asdfghjklñ","zxcvbnm")
    if(q.size==w.size && q.indices.count{q[it]!=w[it]}==1){val j=q.indices.first{q[it]!=w[it]};for(row in rows){val a=row.indexOf(q[j].toChar());val b=row.indexOf(w[j].toChar());if(a>=0 && b>=0 && abs(a-b)==1)return 0}}
    if(q.size==w.size && q.indices.count{q[it]!=w[it]}==2){val changed=q.indices.filter{q[it]!=w[it]};if(changed[1]==changed[0]+1 && q[changed[0]]==w[changed[1]] && q[changed[1]]==w[changed[0]])return 0}
    return 1
}
fun top(q: String,result: Search,freq: Map<String,Int>,lang: String): List<String> {
    val cp=points(q)
    return listOf(q)+result.alternatives.sortedWith(compareBy<String>({distance(points(it),cp)},{adjacencyPenalty(cp,points(it),lang)},{freq[it] ?: Int.MAX_VALUE},{it})).take(7)
}

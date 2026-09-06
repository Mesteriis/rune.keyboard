import java.io.File
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.system.exitProcess

private data class Query(val id:String,val value:String,val category:String,val stratum:String,val best:List<String>,val all:Set<String>)
private fun digest(file:File):String {
 val hash=MessageDigest.getInstance("SHA-256");val buffer=ByteArray(1024*1024)
 file.inputStream().use { input -> while(true){val n=input.read(buffer);if(n<0)break;hash.update(buffer,0,n)} }
 return hash.digest().joinToString(""){"%02x".format(it.toInt() and 255)}
}
private fun verifyFile(root:File,name:String){check(digest(File(root,name))==Frozen.files.getValue(name)){"FIXTURE_HASH"}}
object LexiconVerifyMain {
 @JvmStatic fun main(args:Array<String>){
  val guard=Thread({Thread.sleep(180_000);println("VERIFY\tTIMEOUT");System.out.flush();Runtime.getRuntime().halt(124)},"fixture-verification-deadline");guard.isDaemon=true;guard.start()
  try {check(args.size==2);val root=File(args[0]);for(name in Frozen.files.keys)verifyFile(root,name);println("DEX\t${digest(File(args[1]))}");println("VERIFY\tPASS\t${Frozen.files.size}");exitProcess(0)}
  catch(t:Throwable){println("VERIFY\tFAIL\t${t.javaClass.simpleName}");exitProcess(2)}
 }
}
object LexiconAndroidMain {
 @Volatile private var stage="startup"
 @Volatile private var currentId="none"
 private fun memory(label:String){println("MEM\t$label\t${Platform.memory().joinToString("\t")}")}
 @JvmStatic fun main(args:Array<String>){
  val finished=AtomicBoolean(false)
  try {
   check(args.size==6){"ARGS"}
   val root=File(args[0]);val language=args[1];val format=args[2];val profile=args[3];val mode=args[4];val timeoutSeconds=args[5].toInt()
   check(language in listOf("en","es","ru")&&format in listOf("front","trie","delete"))
   check(profile in listOf("development","smoke")&&mode in listOf("full","cold")&&timeoutSeconds in 30..1800)
   val watchdog=Thread({try{Thread.sleep(timeoutSeconds*1000L)}catch(_:InterruptedException){};if(!finished.get()){println("TIMEOUT\t$stage\t$currentId");System.out.flush();Runtime.getRuntime().halt(124)}},"qualification-deadline")
   watchdog.isDaemon=true;watchdog.start()
   println("META\t${Platform.api()}\t$language\t$format\t$profile\t$mode\t3\t1\t$timeoutSeconds")
   println("MEM_HEADER\tstage\theap_used\theap_committed\tnative_allocated\tpss\tprivate_dirty\trss\tpeak_rss")
   memory("boot")
   stage="fixtures";val fixture="queries/$language.$profile.tsv";verifyFile(root,fixture)
   println("FIXTURE\t${Frozen.files.getValue(fixture)}")
   val queries=File(root,fixture).readLines().map { line ->
    val p=line.split('\t');check(p.size==6){"FIXTURE_COLUMNS"}
    Query(p[0],p[1],p[2],p[3],if(p[4].isEmpty())emptyList()else p[4].split(','),if(p[5].isEmpty())emptySet()else p[5].split(',').toSet())
   }
   check(queries.size==if(profile=="development")240 else if(language=="en")6 else 10)
   check(queries.map{it.id}.distinct().size==queries.size&&queries.all{eligible(it.value)})
   memory("fixtures_loaded")
   stage="frequency";val frequencyStart=System.nanoTime();val frequencies=frequency(File(root,"frequency/$language.tsv"));val frequencyEnd=System.nanoTime()
   println("LOAD\tfrequency\t${frequencyEnd-frequencyStart}");memory("frequency_loaded")
   stage="index_open";val openStart=System.nanoTime()
   val prefix:PrefixIndex?=when(format){
    "front"->SortedIndex(Front(File(root,"assets/$language.front")),LengthBounds(File(root,"assets/$language.front.lengths")))
    "trie"->PackedTrie(File(root,"assets/$language.trie"),LengthBounds(File(root,"assets/$language.trie.lengths")))
    else->null
   }
   val deletion=if(format=="delete")DeleteIndex(File(root,"assets/$language.delete"),Front(File(root,"assets/$language.front")))else null
   val openEnd=System.nanoTime();println("LOAD\tindex\t${openEnd-openStart}");memory("index_opened")
   fun search(q:String,bounded:Boolean)=prefix?.let{trieSearch(it,q,bounded,useLengthPruning=true)}?:deletion!!.search(q,bounded,usePruning=true)
   var boundedComplete=0;var measuredReference=0
   println("ROW_HEADER\tlanguage\tformat\tprofile\tphase\tid\trepeat\tsearch_ns\ttopn_ns\tcpu_ns\tallocated_bytes\tgc_count\tstates\tverified\trows\treason\texpected\treturned\ttop7_equal\tprohibits_autoreplace")
   fun run(q:Query,bounded:Boolean,phase:String,repeat:Int){
    currentId=q.id;stage=phase
    val allocation=Platform.allocated();val gc=Platform.gcCount();val cpu=Platform.cpuTime();val start=System.nanoTime()
    val result=search(q.value,bounded);val searched=System.nanoTime();val ranked=top(q.value,result,frequencies,language);val ended=System.nanoTime()
    val cpuDelta=Platform.cpuTime()-cpu;val allocated=Platform.allocated();val gcAfter=Platform.gcCount()
    check(result.eligible&&ranked.first()==q.value&&ranked.size<=8){"RESULT_CONTRACT"}
    check(result.alternatives.distinct().size==result.alternatives.size&&result.alternatives.all{it in q.all}){"NON_ORACLE"}
    val equal=ranked.drop(1)==q.best
    if(!bounded||!result.exhausted)check(!result.exhausted&&result.alternatives.toSet()==q.all&&equal){"EXACT_REFERENCE"}
    if(bounded)check(result.states<=8192&&result.verified<=64&&result.prohibitsAutoReplace==result.exhausted){"CAPS"}
    if(phase=="reference")measuredReference++
    if(phase=="bounded"&&!result.exhausted)boundedComplete++
    println("ROW\t$language\t$format\t$profile\t$phase\t${q.id}\t$repeat\t${searched-start}\t${ended-start}\t$cpuDelta\t${if(allocation<0||allocated<0)-1 else allocated-allocation}\t${if(gc<0||gcAfter<0)-1 else gcAfter-gc}\t${result.states}\t${result.verified}\t${result.evaluatedRows}\t${result.exhaustionReason}\t${q.all.size}\t${result.alternatives.size}\t$equal\t${result.prohibitsAutoReplace}")
   }
   run(queries.first(),false,"cold_first",0);memory("first_query")
   if(mode=="full"){
    // Entire predeclared corpus warms every reader; no convenient subset is substituted.
    for(q in queries)run(q,false,"warmup",0)
    memory("warmup_complete")
    repeat(3){repeat->for(q in queries){run(q,false,"reference",repeat);run(q,true,"bounded",repeat)}}
    memory("measure_complete");System.gc();System.runFinalization();memory("post_gc_requested")
    check(measuredReference==queries.size*3){"INCOMPLETE_REFERENCE"}
   }
   println("DONE\tPASS\t${queries.size}\t$measuredReference\t$boundedComplete")
   finished.set(true);watchdog.interrupt();exitProcess(0)
  }catch(t:Throwable){finished.set(true);println("FAIL\t$stage\t$currentId\t${t.javaClass.simpleName}");System.out.flush();exitProcess(2)}
 }
}

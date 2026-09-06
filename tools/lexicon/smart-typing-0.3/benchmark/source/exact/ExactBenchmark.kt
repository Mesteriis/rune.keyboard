import java.io.File
import java.security.MessageDigest
import kotlin.system.exitProcess

private fun sha(file:File):String {
 val hash=MessageDigest.getInstance("SHA-256");val buffer=ByteArray(1048576)
 file.inputStream().use{f->while(true){val n=f.read(buffer);if(n<0)break;hash.update(buffer,0,n)}}
 return hash.digest().joinToString(""){"%02x".format(it.toInt() and 255)}
}
object ExactVerifyMain {
 @JvmStatic fun main(args:Array<String>){
  val guard=Thread({Thread.sleep(180000);println("TIMEOUT\t0\t-1");System.out.flush();Runtime.getRuntime().halt(124)})
  guard.isDaemon=true;guard.start()
  try {
   check(args.size==3)
   for((name,hash) in Frozen.files)check(sha(File(args[0],name))==hash)
   for((lang,hash) in ExactFrozen.queries)check(sha(File(args[1],"$lang.tsv"))==hash)
   println("DEX\t${sha(File(args[2]))}");println("MANIFEST\t${ExactFrozen.manifest}")
   println("VERIFY\tPASS\t${Frozen.files.size}\t${ExactFrozen.queries.size}");exitProcess(0)
  }catch(_:Throwable){println("VERIFY\tFAIL");exitProcess(2)}
 }
}
private data class ExactQuery(val id:Int,val cohort:Int,val label:Int,val key:String)
object ExactAndroidMain {
 @Volatile private var stage=0
 @Volatile private var currentId=-1
 private fun memory(id:Int){println("MEM\t$id\t${Platform.memory().joinToString("\t")}")}
 @JvmStatic fun main(args:Array<String>){
  try {
   check(args.size==5)
   val base=File(args[0]);val own=File(args[1]);val lang=args[2];val format=args[3];val timeout=args[4].toInt()
   check(lang in listOf("en","es","ru")&&format in listOf("front","trie","delete")&&timeout in 30..600)
   val guard=Thread({Thread.sleep(timeout*1000L);println("TIMEOUT\t$stage\t$currentId");System.out.flush();Runtime.getRuntime().halt(124)})
   guard.isDaemon=true;guard.start()
   println("META\t${Platform.api()}\t$lang\t$format\t277\t1\t5\t$timeout")
   println("MANIFEST\t${ExactFrozen.manifest}");memory(0)
   stage=1;val fixture=File(own,"$lang.tsv");check(sha(fixture)==ExactFrozen.queries.getValue(lang))
   val queries=fixture.readLines().map{line->val p=line.split('\t');check(p.size==6);ExactQuery(p[0].toInt(),p[1].toInt(),p[2].toInt(),p[3])}
   check(queries.size==277&&queries.map{it.id}.distinct().size==277)
   check(queries.count{it.cohort==0}==240&&queries.count{it.cohort==1}==18&&queries.count{it.cohort==2}==18&&queries.count{it.cohort==3}==1)
   check(queries.all{it.label in 0..2 && (it.key.isEmpty()==(it.label==2)) && canonical(it.key)==it.key})
   memory(1);stage=2
   val started=System.nanoTime()
   val prefix:PrefixIndex?=when(format){
    "front"->SortedIndex(Front(File(base,"assets/$lang.front")),LengthBounds(File(base,"assets/$lang.front.lengths")))
    "trie"->PackedTrie(File(base,"assets/$lang.trie"),LengthBounds(File(base,"assets/$lang.trie.lengths")))
    else->null
   }
   val deletion=if(format=="delete")DeleteIndex(File(base,"assets/$lang.delete"),Front(File(base,"assets/$lang.front")))else null
   println("OPEN\t${System.nanoTime()-started}");memory(2)
   // DeleteIndex has no distinct exact API: its required Front owns membership.
   fun exact(key:String):Boolean=prefix?.exact(key)?:deletion!!.front.exact(key)
   var measured=0;var foundTotal=0
   fun run(q:ExactQuery,phase:Int,pass:Int){
    stage=phase;currentId=q.id
    val gc=Platform.gcCount();val allocation=Platform.allocated();val cpu=Platform.cpuTime();val start=System.nanoTime()
    val found=exact(q.key)
    val elapsed=System.nanoTime()-start;val cpuDelta=Platform.cpuTime()-cpu;val allocated=Platform.allocated();val gcAfter=Platform.gcCount()
    check(found==(q.label==1))
    if(found)foundTotal++
    if(phase==5)measured++
    println("ROW\t$phase\t${q.id}\t$pass\t${q.cohort}\t${q.label}\t$elapsed\t$cpuDelta\t${if(allocated<0||allocation<0)-1 else allocated-allocation}\t${if(gcAfter<0||gc<0)-1 else gcAfter-gc}\t1")
   }
   run(queries.first(),3,0);memory(3)
   for(q in queries)run(q,4,0)
   memory(4)
   repeat(5){pass->for(i in queries.indices)run(queries[(i+pass*37)%queries.size],5,pass)}
   check(measured==1385);memory(5)
   println("DONE\tPASS\t277\t$measured\t$foundTotal");exitProcess(0)
  }catch(_:Throwable){println("FAIL\t$stage\t$currentId");System.out.flush();exitProcess(2)}
 }
}

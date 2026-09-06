import android.os.Build
import android.os.Debug
import java.io.File
object Platform {
 fun api()=Build.VERSION.SDK_INT
 fun allocated():Long=try{Debug.getRuntimeStat("art.gc.bytes-allocated")?.toLongOrNull()?:-1}catch(_:Exception){-1}
 fun gcCount():Long=try{Debug.getRuntimeStat("art.gc.gc-count")?.toLongOrNull()?:-1}catch(_:Exception){-1}
 fun cpuTime():Long=Debug.threadCpuTimeNanos()
 fun memory():LongArray {
  val runtime=Runtime.getRuntime();val info=Debug.MemoryInfo();Debug.getMemoryInfo(info)
  var rss=-1L;var peak=-1L
  try{File("/proc/self/status").forEachLine{line->
   if(line.startsWith("VmRSS:"))rss=line.substringAfter(':').trim().substringBefore(' ').toLong()*1024
   if(line.startsWith("VmHWM:"))peak=line.substringAfter(':').trim().substringBefore(' ').toLong()*1024
  }}catch(_:Exception){}
  return longArrayOf(runtime.totalMemory()-runtime.freeMemory(),runtime.totalMemory(),Debug.getNativeHeapAllocatedSize(),info.totalPss*1024L,info.totalPrivateDirty*1024L,rss,peak)
 }
}

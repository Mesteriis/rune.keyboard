import java.lang.management.ManagementFactory
object Platform {
 private val bean=ManagementFactory.getThreadMXBean() as com.sun.management.ThreadMXBean
 init{if(bean.isThreadAllocatedMemorySupported)bean.isThreadAllocatedMemoryEnabled=true}
 fun api()=-1
 fun allocated():Long=if(bean.isThreadAllocatedMemoryEnabled)bean.getThreadAllocatedBytes(Thread.currentThread().id)else -1
 fun gcCount():Long=ManagementFactory.getGarbageCollectorMXBeans().sumOf{it.collectionCount}
 fun cpuTime():Long=bean.currentThreadCpuTime
 fun memory():LongArray {val r=Runtime.getRuntime();return longArrayOf(r.totalMemory()-r.freeMemory(),r.totalMemory(),-1,-1,-1,-1,-1)}
}

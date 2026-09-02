package io.github.mesteriis.rune.keyboard.intelligence.inference

import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.intelligence.client.LatestReplyGuard
import io.github.mesteriis.rune.keyboard.intelligence.inference.*
import io.github.mesteriis.rune.keyboard.intelligence.storage.*
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelManifestParser
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

private fun CountDownLatch.done() = check(await(3, TimeUnit.SECONDS)) { "test timeout" }
private fun input(id: Long) = ScoringInput(ScoringToken(1, id, id, listOf(3, 4)), "prefix", listOf(" a", " b"))
// Existing worker infrastructure cases use an isolated deterministic CPU source; production uses Process CPU.
private fun testWorker(engine: ScoringEngine, idleMillis: Long = 60_000) = LatestScoringWorker(engine, idleMillis,
    ModelDutyOwner { ModelDutySample(System.nanoTime() / 1_000_000, 0) }, ScheduledModelDutyChecks())
private fun success(input: ScoringInput) = ScoringReply(input.token, 0, 1, listOf(NumericScore(3,-1.0,1),NumericScore(4,-2.0,2)))
private class FakeEngine : ScoringEngine {
    val first = CountDownLatch(1); val release = CountDownLatch(1); val cancelled = CountDownLatch(1)
    val unloaded = CountDownLatch(1); val closed = CountDownLatch(1)
    val seen = CopyOnWriteArrayList<Long>(); val unloads = AtomicInteger(); val active = AtomicBoolean()
    override fun score(request: ScoringInput, cancelled: AtomicBoolean): ScoringReply {
        check(active.compareAndSet(false,true)); seen += request.token.requestId
        if (request.token.requestId == 1L) { first.countDown(); release.done() }
        active.set(false); return success(request)
    }
    override fun cancel() { cancelled.countDown() }
    override fun unload() { check(!active.get()); unloads.incrementAndGet(); unloaded.countDown() }
    override fun close() { check(!active.get()); closed.countDown() }
}
class ScoringInfrastructureTest {
    @get:org.junit.Rule val temporary = org.junit.rules.TemporaryFolder()
    private val args: Array<String> by lazy {
        val manifest = temporary.newFile("manifest.json")
        manifest.writeText(MANIFEST)
        arrayOf(temporary.root.path, manifest.path)
    }
    @org.junit.Test fun boundedContracts() {
        fun rejects(block:()->Unit) { check(runCatching(block).isFailure) }
        rejects { ScoringInput(ScoringToken(1,0,1,listOf(0)), "😀".repeat(1025), listOf("x")) }
        rejects { ScoringInput(ScoringToken(1,0,1,listOf(0)), "\uD800", listOf("x")) }
        rejects { ScoringInput(ScoringToken(1,0,1,listOf(0)), "", listOf("")) }
        rejects { ScoringToken(1,0,1,listOf(0,0)) }
        rejects { NumericScore(1,Double.NaN,1) }
        val ids=mutableListOf(1); val token=ScoringToken(1,0,1,ids);ids[0]=2;check(token.candidateIds==listOf(1))
    }
    @org.junit.Test fun replacingPending() {
        val engine=FakeEngine(); val worker=testWorker(engine);val done=CountDownLatch(1)
        val replies=CopyOnWriteArrayList<Long>();val finished=AtomicInteger()
        worker.submit(input(1), { replies+=it.token.requestId }, {finished.incrementAndGet()});engine.first.done()
        worker.submit(input(2), { replies+=it.token.requestId }, {finished.incrementAndGet()})
        engine.cancelled.done() // completes while first score is still blocked
        worker.submit(input(3), { replies+=it.token.requestId;done.countDown() }, {finished.incrementAndGet()})
        check(engine.seen==listOf(1L));engine.release.countDown();done.done();worker.close();engine.closed.done()
        check(engine.seen==listOf(1L,3L) && replies==listOf(3L));check(finished.get()==3)
    }
    @org.junit.Test fun callbackDeathCancellation() {
        val engine=FakeEngine();val worker=testWorker(engine);val replies=CopyOnWriteArrayList<Long>()
        worker.submit(input(1), {replies+=it.token.requestId});engine.first.done()
        worker.submit(input(2), {replies+=it.token.requestId});worker.cancel(1,2)
        engine.release.countDown();worker.close();engine.closed.done();check(replies.isEmpty());check(engine.seen==listOf(1L))
    }
    @org.junit.Test fun idleUnload() {
        val engine=FakeEngine();val worker=testWorker(engine,30);val done=CountDownLatch(1)
        worker.submit(input(1), {done.countDown()});engine.first.done();check(engine.unloads.get()==0)
        engine.release.countDown();done.done();engine.unloaded.done();check(engine.unloads.get()==1)
        worker.close();engine.closed.done()
    }
    @org.junit.Test fun memoryAndModelInvalidation() {
        val engine=FakeEngine();val worker=testWorker(engine);val replies=AtomicInteger()
        worker.submit(input(1), {replies.incrementAndGet()});engine.first.done()
        worker.submit(input(2), {replies.incrementAndGet()});worker.invalidate();engine.cancelled.done()
        check(engine.unloads.get()==0);engine.release.countDown();engine.unloaded.done();worker.close();engine.closed.done()
        check(replies.get()==0 && engine.seen==listOf(1L))
    }
    @org.junit.Test fun staleReplyGuard() {
        val guard=LatestReplyGuard();val token=input(1).token
        guard.attach(1,false);check(!guard.shouldBind() && !guard.begin(token))
        guard.attach(1,true);check(guard.shouldBind() && guard.begin(token));check(guard.accepts(token,1))
        check(!guard.accepts(token,2));check(!guard.accepts(ScoringToken(2,1,1,listOf(3,4)),1))
        check(!guard.accepts(ScoringToken(1,1,1,listOf(4,3)),1))
        check(guard.begin(input(2).token));check(!guard.accepts(token,1));check(!guard.begin(token))
        guard.invalidate();check(!guard.accepts(input(2).token,2));check(guard.shouldBind()) // death may rebind
        guard.attach(null,false);check(!guard.shouldBind())
    }
    @org.junit.Test fun runtimeFailure() {
        val done=CountDownLatch(1);val closed=CountDownLatch(1)
        val engine=object:ScoringEngine {
            override fun score(request:ScoringInput,cancelled:AtomicBoolean):ScoringReply { throw IllegalStateException() }
            override fun cancel() {}; override fun unload() {}; override fun close() {closed.countDown()}
        }
        val worker=testWorker(engine)
        worker.submit(input(2), {check(it.code==ScoringCode.INTERNAL && it.scores.isEmpty());done.countDown()})
        done.done();worker.close();closed.done()
    }
    @org.junit.Test fun readOnlyResolver() {
        val root=File(args[0],"store-test");root.mkdirs();val gate=ModelOperationGate(root)
        check(runCatching {gate.withReadLock {}}.isFailure)
        gate.withLock {} // install owner initializes physical shared lock
        val resolver=ActiveModelResolver(root);check(gate.withReadLock {resolver.resolve()}==null)
        File(root,"active-model.json").writeText("bad")
        check(runCatching {gate.withReadLock {resolver.resolve()}}.isFailure)
        val descriptor=ModelManifestParser.parse(File(args[1]).readText()).copy(sizeBytes=4)
        val name="${descriptor.id}-${descriptor.version}";val version=File(root,"versions/$name");version.mkdirs()
        File(version,"model-manifest.json").writeText(ModelManifestParser.encode(descriptor));File(version,descriptor.fileName).writeText("GGUF")
        val backup=File(root,"active-model.json.bak");backup.writeText(ActiveModelPointerCodec.encode(ActiveModelPointer(name,null)))
        val resolved=gate.withReadLock {resolver.resolve()};check(resolved?.fileSize==4L);check(backup.exists());check(File(root,"active-model.json").readText()=="bad")
        File(version,descriptor.fileName).writeText("truncated");check(runCatching {gate.withReadLock {resolver.resolve()}}.isFailure)
        backup.writeText("x".repeat(1025));check(runCatching {gate.withReadLock {resolver.resolve()}}.isFailure)
        root.deleteRecursively()
    }
}

private const val MANIFEST = """{"schemaVersion":1,"modelId":"rune-text-v1","version":"0.1.0","displayName":"Rune Text 0.1","fileName":"rune-text-v1-0.1.0-q4_k_m.gguf","url":"https://github.com/Mesteriis/rune.keyboard/releases/download/model-rune-text-v0.1.0/rune-text-v1-0.1.0-q4_k_m.gguf","sha256":"7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4","sizeBytes":396704416,"runtimeApi":1,"minimumRuneVersionCode":2,"ggufVersion":3,"architecture":"qwen3","fileType":15}"""

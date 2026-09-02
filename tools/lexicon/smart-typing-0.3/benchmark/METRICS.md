# Resource evidence and API26 allocation limitation

The original full and first exact Android adapters read
`Debug.getRuntimeStat("art.gc.bytes-allocated")` before and after a query.
The initial exact device records contain 45 differences below -1, spread across
all nine processes; the strict exact reducer rejected them. The later exact
adapter returns -1 without reading this stat. Exact-02 matched all 12,465 measured
references and all allocation p95 fields are null. The old full harness remains
verbatim to preserve its measurement identity, but **none of its Android allocated
bytes distributions is admissible evidence**, even if a value is positive.

The API26 source calls this a total, rather than a simple live-heap gauge.
[Android 8.0 Debug documentation](https://android.googlesource.com/platform/frameworks/base/+/android-8.0.0_r1/core/java/android/os/Debug.java#1560)
and [VMDebug's dispatch](https://android.googlesource.com/platform/art/+/android-8.0.0_r1/runtime/native/dalvik_system_VMDebug.cc#413)
lead to [Heap::GetBytesAllocatedEver](https://android.googlesource.com/platform/art/+/android-8.0.0_r1/runtime/gc/heap.cc#1871),
which adds live allocation to freed-ever. During GC, `RecordFree` decrements live
bytes, while freed-ever is updated after the collector returns. These separately
updated counters can yield a decreasing sampled total. Later ART adds an explicit
[monotonic guard](https://android.googlesource.com/platform/art/+/c6371b52df/runtime/gc/heap.cc).
This establishes the invalid measurement assumption, not the precise GC
interleaving responsible for each observed sample.

Clamping a negative difference, discarding selected samples or keeping only a
maximum would not produce a valid per-query allocation count; delayed GC
accounting can contaminate positive intervals as well. Historical records and
summaries are preserved. The portable full aggregation command first validates
all records and produces an additional qualified summary with Android allocation
fields null. It never rewrites the raw summary. Exact retains its existing
unavailability-before-median rule for CPU, allocation and GC optional metrics.

The full and exact DEX identities differ and remain bound to their own records:

| Artifact | SHA-256 |
|---|---|
| Full quiet/cold DEX | `6d17867fb4abca637872e500e0d4c32cb36b29231d8368cd683baa745db6c418` |
| Original exact-01 DEX | `4dd7c033a51af6e9069148b1706da4f12d4437359c4a056f19dd2fd7be9d29ad` |
| Corrected exact-02 DEX | `89449fc9e5f4bdb5decde1741a7e5d17528ad2277cad11195a829c10329ef11b` |

Removing unsupported stat calls changes observation overhead as well as DEX
bytes. Exact timing conclusions use exact-02; old membership correctness remains
independent. Full latency comparisons remain on the same full DEX for every
format and do not incorporate exact timing samples.

PSS/RSS/private dirty are process resident-memory checkpoints, influenced by
mapped/touched pages and collection timing. Heap used/committed and native
allocated are checkpoint observations, not cumulative allocation volume.
The common full-profile frequency map has its own load/checkpoint, while the exact
profile does not need to load frequencies. Exact keeps the identical files and
format sidecars in preflight/open scope. Its memory numbers therefore should not
be substituted for a complete candidate-generation process footprint.

CPU time and GC counts do not establish battery use or energy efficiency. No
energy, power, thermal or physical-device test is in this package. Fresh processes
reset runtime state; preflight itself touches every file, so they do not establish
cold storage/page-cache latency. With three cold observations, reported maxima
and nearest-rank quantiles describe those three runs only.

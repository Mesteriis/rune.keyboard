# Frozen lexicon format qualification tools

Packed trie is selected for the next integration step. In the quiet API26 run,
its complete top-N p95 beats front coding and deletion postings with positive
paired 95% confidence intervals in EN, ES and RU. The separate exact lookup run
also favors trie. The APK size tie-break was not invoked. This chooses a format;
it does not qualify the future weighted production candidate generator.

| Language | Front complete p95, ms | Trie complete p95, ms | Delete complete p95, ms | Trie exact development p95, ns |
|---|---:|---:|---:|---:|
| EN | 131.762584 | 4.018125 | 23.591459 | 8,875 |
| ES | 173.228125 | 5.092875 | 230.839792 | 10,583 |
| RU | 288.389833 | 8.120625 | 393.686417 | 13,125 |

`evidence/decision.json` contains all paired intervals, capped completion counts,
actual APK contributions and cold memory observations. The original summaries
are retained byte-for-byte. The first full run is diagnostic because a host
Gradle build overlapped it; only `development-quiet` decides the format.

All Android allocation distributions produced by the original full harness are
**unsupported**, including positive deltas. Exact-02 disables that optional
metric and reports unavailable. Read [METRICS.md](METRICS.md) before using the raw
summaries. Heap/RSS/PSS, CPU, GC and wall time have separate meanings; none is an
energy or battery measurement. Three fresh processes per format are not a
statistical cold p95 estimate. Preflight reads all assets, so the OS page cache is
unknown and likely warm. This is API26 emulator evidence, not physical-device
performance qualification.

## Package and provenance

`source/common/LexiconPrototype.kt` contains the **unchanged** three full-data
readers. Front uses its length sidecar; trie uses its length sidecar; deletion
uses both deletion postings and front coding. Frequency ranks remain a separate
CC-BY-SA 4.0 TSV. All source attribution and component licenses travel through
`../notices`, `../source-lock.json` and `../frozen-output-manifest.json` from the
committed pinned lexicon pipeline. The small preserved upstream prototype notice
is historical: its statement that that prototype had no APK does not describe
these later asset-only APK measurements.

The full harness computes the entire candidate neighborhood before common top-7
ranking. Its ranking key is `(unit unrestricted DL, static adjacency penalty,
frequency rank, lexical order)`; the original is first. Radius is 1 below five
codepoints and 2 otherwise, maximum input length is 32 codepoints. The lexical
ordering equivalence in the independent oracle is qualified for the frozen BMP
wordforms. This is **not weighted DL** and is not the later best-first/DFS top-N
prototype. No format gets a different ranker, radius, vocabulary or query list.

The capped profile uses 8192 inspected search states and 64 verified candidates.
Caps are reported separately and never enter the speed decision as fast results.
Trie completes only EN 61/240, ES 66/240 and RU 18/240 in this exhaustive-neighborhood
implementation. Thus the selected format alone does not solve the production
budget. Exhaustion prohibits automatic replacement. Reusing unit-distance pruning
for weighted ranking requires a separately proven admissible bound or full
weighted verification; these results do not provide that proof.

`manifests/source-origins.json` records historical source names and SHA-256s;
these names are provenance, not required runtime directories. Common files are
stored once and copied into an isolated build directory. Readers, builders,
harnesses and reducers are verbatim; only APK tool SDK discovery is adapted.
`bench.py` supplies portable orchestration and `records.py` adds strict record
completeness checks and a separately qualified full summary. No index or DEX
binary is committed. `package-manifest.json` identifies every package file.

## Prepare from committed pipeline outputs

Python 3.10+, JDK 17, cached Kotlin 2.2.10 jars, Android platform `android-37.0`,
Android build tools 36.0.0 and a C++17 compiler are required for a fresh build.
No tool downloads dependencies or invokes Gradle/ADB. Existing local dependency
paths are supplied explicitly and never saved in reports. See
`manifests/toolchain.json` for the precise jar identities and cached packaging
binary reference hashes. The historical APK report did not snapshot executable
hashes; these references describe the cached toolchain at promotion. A different host's aapt2/zipalign binaries get distinct recorded
hashes. D8 and Android stub jars must match the lock.

Run from the repository root. `build/lexicon-inputs` below is an **already
reproduced** output directory of the committed pipeline, not a new dataset:

```sh
python3 tools/lexicon/smart-typing-0.3/pipeline.py --build-dir build/lexicon-inputs verify
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py check
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py prepare --build-dir build/lexicon-benchmark-001 --source-build-dir build/lexicon-inputs
```

Preparation hashes every canonical wordlist and frequency TSV, preserves notices
and frozen queries, and independently rechecks all 831 exact labels by streaming
the complete canonical dictionaries. It does not read any reserved/holdout query
files or regenerate the query selection. A new dedicated build directory is
required; failed partial preparation is retained and requires another directory.
The existing pipeline build-tree guard rejects pre-existing escaping symlinks,
including leaf files. There is one writer per build directory; this is not a
sandbox against concurrent adversarial filesystem mutation.

For already built indices, point `--index-cache` at a directory containing the
15 `en/es/ru.front`, `.trie`, `.delete`, `.front.lengths`, `.trie.lengths` files:

```sh
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py indices --build-dir build/lexicon-benchmark-001 --index-cache "$LEXICON_INDEX_CACHE"
```

Every cached asset's byte count and hash must match the frozen measured manifest.
Without `--index-cache`, `indices` runs the unchanged Python front/trie/length
builders and C++ deletion builder sequentially, then checks all 15 frozen hashes.
This is the deliberately expensive reconstruction path, on a little-endian host:

```sh
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py indices --build-dir build/lexicon-benchmark-001 --cxx clang++
```

The full canonical inputs, all formats and separate frequency/notices are staged
under this build only. Internal hardlinks share generated immutable index bytes.
No data is added to the application APK or production assets.

## Compile and measure actual asset APK contribution

Set `BENCH_JAVA_HOME`, `BENCH_ANDROID_SDK` and `BENCH_JAR_CACHE` to existing local
locations. The last is the Gradle Maven artifact cache directory ending in
`modules-2/files-2.1`; using it does not run Gradle.

```sh
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py compile --build-dir build/lexicon-benchmark-001 --java-home "$BENCH_JAVA_HOME" --sdk "$BENCH_ANDROID_SDK" --jar-cache "$BENCH_JAR_CACHE"
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py package-apk --build-dir build/lexicon-benchmark-001 --sdk "$BENCH_ANDROID_SDK"
```

Compilation uses at most two active JVM processors, 768 MiB heap, JVM target 1.8
and D8 min API 26. The source sets and compiler/D8 arguments match the measured
harnesses. New `full/reports/build-identity.json` and `exact/reports/build-identity.json`
record the actual new DEX and source hashes. A rebuilt DEX is never assigned a
historical identity, even if code is unchanged. Run results must verify that
specific DEX. Each child build has a bounded timeout and raw compiler diagnostics
are captured instead of exposing paths or input fields.

APK measurement runs actual `aapt2 link` and `zipalign -f 4`, with one identical
min/target-26, no-code manifest and a shared baseline of normally compressed
frequency/notices. Index extensions `front`, `trie`, `delete`, `lengths` use `-0`
(storage); each ZIP entry's type and byte hash are checked. Contributions are
aligned per-format APK size minus its same-language baseline APK, not a raw-size
or gzip proxy. Historical contributions in bytes:

| Language | Front + lengths | Trie + lengths | Delete + front |
|---|---:|---:|---:|
| EN | 1,118,751 | 4,903,219 | 31,193,180 |
| ES | 7,342,963 | 22,517,911 | 175,923,714 |
| RU | 17,153,177 | 40,605,879 | 380,837,612 |

These are unsigned asset-only fixtures, not signed application release APK sizes.
The source pipeline licenses remain attached to their respective components.

## Authorized device execution, separate from host build

The tool itself never contacts a device. After choosing the already authorized
API26 target outside report files, and after other host builds have stopped, the
operator can stage the public fixture directories and runners below. The fixed
remote roots are task-owned; do not substitute an application data directory.
No serial, process ID, or raw input text belongs in evidence.

```sh
adb shell mkdir -p /data/local/tmp/rune-lexicon-pr6 /data/local/tmp/rune-lexicon-exact-pr6
adb push build/lexicon-benchmark-001/full/fixtures /data/local/tmp/rune-lexicon-pr6/
adb push build/lexicon-benchmark-001/full/bin/benchmark-dex.jar /data/local/tmp/rune-lexicon-pr6/
adb push build/lexicon-benchmark-001/full/device/run.sh /data/local/tmp/rune-lexicon-pr6/
adb push build/lexicon-benchmark-001/exact/fixtures /data/local/tmp/rune-lexicon-exact-pr6/
adb push build/lexicon-benchmark-001/exact/bin/benchmark-dex.jar /data/local/tmp/rune-lexicon-exact-pr6/
adb push build/lexicon-benchmark-001/exact/device/run.sh /data/local/tmp/rune-lexicon-exact-pr6/
adb shell sh /data/local/tmp/rune-lexicon-pr6/run.sh /data/local/tmp/rune-lexicon-pr6 smoke api26-smoke-001 300
adb pull /data/local/tmp/rune-lexicon-pr6/results-api26-smoke-001 build/lexicon-benchmark-001/full/reports/device-api26-smoke-001
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py aggregate --build-dir build/lexicon-benchmark-001 --kind full --records build/lexicon-benchmark-001/full/reports/device-api26-smoke-001
adb shell sh /data/local/tmp/rune-lexicon-pr6/run.sh /data/local/tmp/rune-lexicon-pr6 development api26-quiet-001 900
adb pull /data/local/tmp/rune-lexicon-pr6/results-api26-quiet-001 build/lexicon-benchmark-001/full/reports/device-api26-quiet-001
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py aggregate --build-dir build/lexicon-benchmark-001 --kind full --records build/lexicon-benchmark-001/full/reports/device-api26-quiet-001
adb shell sh /data/local/tmp/rune-lexicon-pr6/run.sh /data/local/tmp/rune-lexicon-pr6 cold api26-cold-001 120
adb pull /data/local/tmp/rune-lexicon-pr6/results-api26-cold-001 build/lexicon-benchmark-001/full/reports/device-api26-cold-001
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py aggregate --build-dir build/lexicon-benchmark-001 --kind full --records build/lexicon-benchmark-001/full/reports/device-api26-cold-001
adb shell sh /data/local/tmp/rune-lexicon-exact-pr6/run.sh api26-exact-001 90
adb pull /data/local/tmp/rune-lexicon-exact-pr6/results-api26-exact-001 build/lexicon-benchmark-001/exact/reports/device-api26-exact-001
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py aggregate --build-dir build/lexicon-benchmark-001 --kind exact --records build/lexicon-benchmark-001/exact/reports/device-api26-exact-001
```

Use a fresh tag for every run: runners refuse existing results. Smoke's original
26 queries are an initial compatibility check only. Full selection requires all
720 development queries in all three formats; no failures or slow cases are
filtered. The full runner rotates format order by language, and cold rotates
again over three fresh processes. Each process has its own wall-clock watchdog;
full watchdog 30–1800 seconds, exact 30–600, preflight 180. Normal default nine
full processes have a worst-case watchdog budget of 9×900 seconds plus preflight;
this is intentionally bounded qualification work, not an IME code path.

Read `qualified-*.json` for the full profile's metric interpretation. The legacy
`summary-*.json` remains a raw reducer artifact containing unsupported allocation
numbers and is never silently overwritten. Missing records, duplicated rows,
wrong preflight/fixture/DEX hashes, failed references or incomplete processes
prevent aggregate success. Exact's unavailable optional metric is null if any
repetition is unavailable, before computing a median. Built-in parse errors are
reported by exception type; no raw numeric field is echoed.

## Frozen oracle, checks and history

The predeclared development fixture has 240 queries per language: six error
categories × 40, stratified 84 frequent / 78 mid-frequency / 78 unranked forms.
Each source is unique and the preserved source-hash split excludes the reserved
portion. Both manifests and the small public query/oracle fixtures are retained.
The exact fixture adds 18 present, 18 independently absent structural controls and
one empty key per language. Structural controls are separate pools, not a claim
about natural positive lookup distribution. One control per category/stratum can
produce degenerate bootstrap intervals; the 720-key development pool remains the
format latency comparison.

Full timing is end-to-end search plus common top-N; wall time and thread CPU are
separate. Each format warms on the entire profile once, then runs three complete
and three capped repetitions per query. The full decision uses per-query medians,
nearest-rank p95 and 2000 paired bootstrap replicates resampling within category ×
frequency-stratum with seed 30902026. Exact uses one full warmup and five measured
passes, rotating query offset by 37 each pass; 831 references × 3 formats × 5 =
12,465 measured comparisons, plus warmup and first-query observations. It calls
only exact membership. Delete's exact path is its required front-coded reader,
while both delete/front files are opened; sidecars match the full comparison.

```sh
python3 tools/lexicon/smart-typing-0.3/benchmark/test_contracts.py
# Optional, expensive independent C++ full-scan oracle regeneration:
python3 tools/lexicon/smart-typing-0.3/benchmark/bench.py oracle --build-dir build/lexicon-benchmark-001 --cxx clang++
```

The optional oracle validates all 720 development and 26 smoke neighborhoods and
common top-7 outputs against the retained fixtures, using independent unrestricted
DL and ranking implementations. It never changes the fixture or selection and
has a 3600-second timeout per language/profile child. Do not run it alongside
measurements. Promotion tests validate preserved numerical record completeness,
metadata, source identities, p95/coverage, unavailable-metric behavior, input
redaction and build boundaries without recompiling or running a device.

`PROTOCOL.md` documents all record columns. Historical records are losslessly
compressed under `evidence/` with a per-record SHA manifest; `records.historical_records()`
loads and verifies them without writing files. Original exact-01's 45 invalid
allocation deltas are preserved as diagnostic evidence, never passed off as
exact-02. Rebuilds are new runs; historical hashes are not templates to rewrite.

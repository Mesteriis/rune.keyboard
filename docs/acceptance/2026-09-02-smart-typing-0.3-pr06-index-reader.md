# Smart Typing 0.3 — PR6 index selection and reader checkpoint

Date: 2026-09-02. Base: `c29aed0fd279caa610a4eb07ef8c721689c94986`. This checkpoint selects and implements the read-only reader. It does not close PR6 or enable spelling in the IME.

## Format decision

Packed trie won the quiet API26 complete-neighborhood comparison for all languages. All paired 95% intervals favor trie over both front coding and deletion postings, so the APK-size tie-break was not invoked. The independent exact lookup profile also favors trie. Full p95 in milliseconds: EN 4.018125, ES 5.092875, RU 8.120625. Exact development p95 in nanoseconds: EN 8875, ES 10583, RU 13125.

The reproducible tools, measured source identities, all paired intervals, actual asset-only APK sizes, cold-process observations and 68 original numeric transcripts are under `tools/lexicon/smart-typing-0.3/benchmark/`. The first run overlapping host Gradle remains diagnostic. All original Android allocation-volume distributions are unsupported; corrected exact-02 reports allocation unavailable. No records are filtered to improve latency or allocation statistics.

These measurements use the old unit-distance contract. The bounded trie completed only EN 61/240, ES 66/240, RU 18/240; these low rates are not hidden by the fast complete-reference times. Format selection does not prove weighted candidate completeness, useful AutoReplace coverage, cold-storage behavior or physical energy.

## Reader

The implementation validates code-pinned typed metadata, asset lengths/hashes, all graph/ordinal/Unicode/length/rank invariants and the full canonical terminal digest before exposing immutable maps. Android mapping uses exact read-only APK regions via openFd with no extraction fallback or unsafe unmapping.

RTR1/LEN1 retain the measured format. Separate RNK1 ranks derive directly from pinned canonical and frequency streams; no experimental FRB1 artifact is required. EN/ES/RU rank assets total 8,904,360 bytes and match the previously checked ordinal ranks. This is component size, not an APK measurement. Licenses and notices remain separate.

Exact lookup and primitive unrestricted unit-radius DFS share the generator's 8192-state/64-verification budget. No unit-top-seven prefilter or rank pruning is used. Exhaustion remains incomplete with AutoReplace veto. Query scratch clears on every exit; no query/visitor/control persists in the reader.

## Checks

- Independent benchmark promotion review: approved proposal `036461131c69cf12460fd3681ec2894ae5c3acdb94c1fc9822a9455da9c506b8`; all 55 files/68 historical transcripts verified.
- Integrated benchmark contracts: **23 PASS**. Fresh root CLI prepare, cached-index identity validation and portable Kotlin/D8 compilation: **PASS**. No new device benchmark or APK-size observation is claimed from compilation.
- Independent reader review: two P2 fixes approved; standard JVM temp handling and direct rank derivation remove hidden harness/artifact dependencies. Final proposal `28b8b24d27f62e12d4883b16c880d4c40acaf49b35cfe9bb858af9bdd9e48476`.
- Reader host tests: **15 PASS**, including 64 independent finite edit-graph neighborhoods. Full structural/canonical load checked 2,226,075 terminals; 828 nonempty exact references and three empty-unavailable controls passed. This was not 2.2 million exact calls.
- Integrated direct rank-builder regressions: **4 PASS**; all three rank assets and generated metadata remain byte-identical.
- Integrated fresh JVM: **374 PASS**, zero failures/errors/skips, 46 tasks executed.
- Full prescribed lint/build/privacy/dependency/native gates: **PASS**, 238 tasks / 48 executed.

Build logs live under `build/smart-typing-0.3/pr06-packed-reader-*` and `pr06-benchmark-*-integrated.log`. Required post-commit JVM results will be recorded against the actual commit in the progress ledger. Ordinary CI now includes the small rank-builder and benchmark contracts; remote execution remains unrun.

## Remaining acceptance

Full dictionary/notice packaging, actual Android open/map/load on API26/API37, measured APK size for RNK1 and the full weighted/cross-language development oracle remain active follow-ups. A latest-request worker and live typing ownership/publication integration remain separate. Deterministic/final-model holdout quality, model request duty limits and physical Fold IME/energy gates are open. Version remains 0.2.0.

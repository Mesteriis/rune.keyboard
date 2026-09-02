# Smart Typing 0.3 — bounded native scoring checkpoint, 2026-09-02

Baseline: `b5400cbadadd29e8ee915a0fb33fb11ec5bebc79`.
Slice parent: `1e100db8e9dce81d3b0c5acc8a636298c8ebef41`.
This checkpoint qualifies PR2 infrastructure and the already integrated PR4/PR5
foundation. It does not qualify a 0.3 release or enable model ranking in the IME.

## Implementation

- Shared evaluator/runtime C++ scoring core: strict UTF-8, 1–8 unique candidate
  IDs, bounded bytes and standalone/full token counts, common full-string token
  prefix, stable log-softmax, summed probability and divergent token count.
  Every variant uses serial teacher forcing with cleared KV. No generated text,
  EOS injection, shared-prefix KV optimization or partial successful result.
- Existing error codes 0–11 preserved; 12–15 append INVALID_REQUEST,
  CONTEXT_TOO_LONG, TOO_MANY_CANDIDATES and SCORING_FAILED. Numeric JNI result
  wire validates size, IDs, ordering, finite scores and counts. All JNI entry
  points contain native exceptions, and handles remain lifecycle-owned.
- Cooperative per-call tokenizer cancellation reaches Unicode preparation,
  QWEN2 pre-split and BPE inner loops. Unsupported presets fail closed. The old
  tokenizer API remains. CMake verifies pristine pinned sources and applies the
  patch only to an archived build-directory copy.
- Request cancellation predicates run after native cancellation reset under the
  admission monitor. A caller first marks its request cancelled, then invokes
  runtime.cancel(). Cancel does not wait for the inference operation monitor.
  The reset-order regression fails against the deliberately reordered mutant.
- Existing fixed runtime self-test remains; no unrestricted generate API exists.

## Provenance

| Input | Verified identity |
| --- | --- |
| llama.cpp gitlink | `36b10154383b60eb15baac2c7a40d2a5f784faa7` |
| Tokenizer patch SHA-256 | `0a043ce8a57b8534ef2f409443d2dd6ecf00042bd9c2b661b31d94618eb4dc95` |
| Inner GGUF bytes | 396704416 |
| Inner GGUF SHA-256 | `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4` |
| GGUF metadata | v3, qwen3, Q4_K_M |
| Legacy 632-sequence tokenizer golden SHA-256 | `d65c09fdad70f012a0ad17a01d9e0a7c1d891136a69c1977633b9152a7fdea00` |

`tools/test-native-scoring/README.md` records reproducible commands, golden
provenance and mandatory/optional test selection. Ordinary CI uses synthetic
fixtures without a model. The new manual workflow selects only artifact
9800688354 and verifies the nested GGUF before use; it has not run remotely.

## Actual local validation

| Gate | Result |
| --- | --- |
| Fresh JVM before commit | PASS, 305/305 (286 app + 19 runtime), no failures/errors/skips |
| Required lint/build/privacy/dependency/native gates | PASS, final run 292 tasks, 19 executed |
| Android test APK assembly | PASS |
| Mandatory host CTest | PASS, 4/4, 1.91 s |
| Host exact-model CTest | PASS, 7/7, 17.30 s |
| Nested artifact extractor tests | PASS, 4/4; actual candidate ZIP also verified |
| Scalar numerical oracle | PASS, 15 comparisons, maximum sum delta 0 |
| Legacy/new tokenization equivalence | PASS, all 632 complete token sequences |
| API26 app Binder/UI suite | PASS, 57/57, 390.754 s |
| API26 ordinary JNI runtime | PASS, 6/6, 0.162 s |
| API26 exact-model runtime | PASS, 1/1, 54.806 s |
| API37 app Binder/UI suite | PASS, 57/57, 476.425 s |
| API37 ordinary JNI runtime | PASS, 6/6, 0.126 s |
| API37 exact-model runtime | PASS, 1/1, 36.626 s |
| New remote CI jobs | BLOCKED pending separately authorized push |
| Physical Fold, battery and thermal measurements | BLOCKED, physical device unavailable at initial inventory |
| Model-assisted quality | FAIL for original frozen Rune Text PR1 suitability; final product pipeline not implemented |
| Immutable model publication | BLOCKED pending physical qualification and separate publication authorization |

Each exact-model Android scenario verified the digest before loading and completed
nine successful requests/27 candidates, two pre-cancelled admissions, one
concurrent CANCELLED result and a successful next request, then unload/reload.
Scenario duration includes hashing, load and many operations: it is not per-key
latency or a battery measurement. Android cancellation does not identify the
internal stage; the real synthetic host tokenizer test proves all eight stages,
including a third checkpoint inside Unicode/pre-split/BPE loops. Primitive and
allocator operations remain cooperatively, not forcibly, interruptible.

## Test fixture corrections and review

Earlier API37 failure waited for an accessibility node before the input/strip
update completed. The regression now observes the expected editor text and waits
for the exact node. Earlier API26 double-space failure used an accessibility
bounds lookup between taps; the driver now resolves bounds once and verifies the
real injected double-tap interval is at most 400 ms. Product timing rules and
assertions remain intact. Earlier logs are retained; their failed runs are not
counted as passes. Independent scoped reviews approved both changes.

Native scoring, cancellation admission, host qualification, extractor/workflow
and optional Android test changes received independent reviews. The current
source diff is whitespace-clean. Fresh JVM rerun after the local commit is
recorded separately with the commit hash in the execution ledger.

Local content-free logs: `build/smart-typing-0.3/pr02-jvm.log`,
`pr02-gates-final.log`, `pr02-all-api26-final.log`, `pr02-all-api37-final.log`,
`pr02-native-api26-final.log`, `pr02-native-api37-final.log`,
`pr02-exact-model-api26.log`, `pr02-exact-model-api37.log`, and
`build/test-native-scoring-test.log`, `build/test-native-scoring-model-test.log`.

Version remains 0.2.0. No push, remote PR or model publication occurred.

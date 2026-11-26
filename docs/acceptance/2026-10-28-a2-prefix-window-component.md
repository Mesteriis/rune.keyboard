# A2: experimental prefix-window component and controller wiring

`ModelPrefixWindow` is a per-session, RAM-only candidate for limiting Rune-owned
model prefixes. It preserves a nonblank short prefix byte-for-byte, excluding one
final ASCII separator from the 256-byte budget. When a prefix grows past that
budget, it retains a suffix of at most 160 bytes where possible (otherwise at
most 256), starting immediately after whitespace at a grapheme boundary. As
text extends, the same start is reused until the retained suffix exceeds the
budget. An unbreakable oversized word, malformed UTF-16 or blank input returns
no prefix; replacement or explicit `clear()` drops the stored anchor.

Seven focused JVM tests cover the 256-byte edge, long Cyrillic and emoji,
grapheme boundaries, hysteresis, malformed surrogate, long words and reset. The
full suite passed 1,385 tests, zero failures or skips. Initially the component
was not called by model request paths; the subsequent opt-in wiring is described
below. It has not been accepted for model scoring or enabled on Fold.

## Opt-in controller wiring

The ordinary spelling request, delayed local-result request and contextual
punctuation model request now accept the window through an internal constructor
flag. The flag defaults to false, and the application does not enable it.
With it enabled, blank or unbreakable oversized prefixes do not produce a
request. Contextual variants are still derived from the full Rune-owned context;
only the prefix passed to scoring is bounded. The window is cleared alongside
the session context, including invalidation and editor teardown. Previous-word
refinement remains unchanged as specified by the review.

Four controller tests exercise short and 256-byte inputs, empty context, long
ordinary and delayed spelling requests, and contextual variants. All 1,389 JVM
tests pass with no skips. With the experimental flag **off**, the actual
two-process Q7 replays for 2,160 and 12,000 rows match their existing baselines;
logs and receipts are under `build/review-a2-disabled-parity-20261028{,-historical}`.
These are model-free default-path replays, not frozen model-score parity and not
evidence for enabling the feature. Native KV reuse, long-context model quality
and Fold latency remain unverified.
The versioned standard-library Python inventory also passed 745 tests across
141 modules with no skips after adding the component to the replay source list.

## Android ICU boundaries

An emulator-only instrumentation test invoked the actual Android ICU grapheme
segmenter and `ModelPrefixWindow` on long synthetic Cyrillic text containing a
family emoji and a combining mark after whitespace. It checked the returned
suffix, word and ICU grapheme boundaries, the UTF-8 cap, hysteresis, the exact
256-byte edge and an unbreakable oversized word. The test passed on API 26 and
API 37 arm64; the task-owned emulators were stopped and deleted. This exercises
the component with those ICU versions, not a model request or every Unicode
sequence. The feature remains disabled in the app.

Raw logs `build/review-a2-icu-api{26,37}-20261028/icu.log` have SHA-256
`710a412db7e7c54c35e10e65571e4153724bdfb820606185ec9539176fd7cc0f` and
`6fa6976baac0eb1174bb1484aa7cae353282f20c595485c64ae95cfb27efc659`.
The instrumentation APK SHA-256 was
`7246585d2172ef99c88d53aad09491447e72e4c91e9b8b0dcf02a967f83db3ae`.

## Host native KV observation

The original Rune Text 0.1 GGUF was SHA-256 verified as
`7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`.
An isolated, instrumented copy of the host scorer records the number of tokens
actually retained after the cache-removal branch. It uses the pinned llama.cpp
revision and source, with no change to the production scorer. Three synthetic
prefixes are exactly the window outputs asserted by `ModelPrefixWindowTest`:
initial overflow, an extension with the same start, and a later window shift.
The scorer reused respectively **0, 69 and 1** tokens. Each warm result was
compared against a new scorer for that request; token counts matched and the
maximum measured score delta was **0**. The probe is a host CPU observation,
not a Fold benchmark or Android runtime acceptance.

The reproducible runner is `tools/eval/smart-typing-0.3/a2_cache_probe.py`;
its receipt at `build/review-a2-native-cache-verified-20261028/receipt.json` binds
the source, generated observed copy, model, executable and native libraries.
The marker-injection unit test and the exact-window JVM test pass. The model
window remains disabled until frozen model-score parity, long-context accuracy
and physical-device performance are qualified.

## Historical holdout request inventory

The retained `final-product-replay-20260906-review-v4/requests-holdout.jsonl`
contains 2,973 requests (RU 994, EN 1,015, ES 964). All prefixes are nonblank;
the maximum UTF-8 size excluding one final ASCII space is 59 bytes, and none
exceeds 256 bytes. Its SHA-256 is
`b790c467d8287ed67ec428dca35f558a140e1853ea948144c38d66f5eb10fd05`;
the adjacent export receipt SHA-256 is
`569c9e0418b2dd174500eeb22904de6afafe5b02298109b739aef4e7b3a0a1a9`.
This is an inventory of a historical request export, not a current controller
replay or a comparison of model scores. It does not cover no-request rows,
long natural contexts, or prove parity with the experimental window enabled.

## Current controller request comparison

On the original 12,000 spelling rows, the same freshly compiled controller
export was run with `rune.replay.prefixWindow` false and true. The complete
`actualModelRequest` values matched, including null requests, identities,
prefixes, candidate IDs and continuations: 1,877 calibration requests and
2,004 holdout requests. No model was called; this is not score or outcome parity.
The raw exports are `build/review-a2-model-requests-20261028/observations.jsonl`
and `window-on/observations.jsonl`, SHA-256 respectively
`2f5da091ce095d583687bad4485dc9be9bfa84f6dcc4693a2670962673ae9675` and
`6a1f6ab76f9a01a72c5811dbdda091850d1d76b893d1e3cd5aee55f0377da5fb`.
The shared compiled JAR SHA-256 is
`5d6f685149d1c0ff57e12bba5075836db82552b5ca9dda3c58a65c99e2f89ed4`.

The original export command returned exit 1 at `CURRENT_POLICY_EXPORT` after
producing all rows: its historical assertion requires no model-free qualification
for every language, while 8,000 current rows report it enabled. That failure is
not a passed frozen replay gate. The window-on run used the same JAR and inputs;
the two request lists were compared directly after checking row counts. Timing
and other observation fields were not compared.

The comparison is now reproducible with
`python3 tools/eval/smart-typing-0.3/pipeline/a2_request_parity.py --output build/<fresh-directory>`.
The final run at `build/review-a2-request-parity-final-20261028` passed with the
same request counts; its source freeze and receipt bind the corpus, inputs,
compiled harness and observations. A unit test rejects changed requests,
missing requests, changed languages and reordered rows. The historical
`CURRENT_POLICY_EXPORT` assertion remains unchanged for its original protocol.

### 2026-11-24 replay from source without model artifacts

After temporary artifacts had been cleaned, the request comparison
failed during source binding because it required the native scorer and
GGUF. The request exporter now binds its corpus, controller and JVM
inputs and runs without those two files. The scored historical replay
still requires both files and verifies their pinned identities. The
separate A2 score tool verifies its own pinned scorer and model digests.

With the app and runtime sources of `123d0a52`, the fresh comparison
matched every request and no-request row across all 12,000 inputs.
Calibration contained 1,877 requests with a 55-byte maximum prefix.
Holdout contained 2,004 requests with a 59-byte maximum prefix. No
request had a blank prefix or exceeded the 256-byte bound after removing
one final ASCII space. The model call count was zero. The request
receipt SHA-256 is
`5998210c61df5e1503829b4560dec5a5448e6b0e4aba9227130bff8a4568f685`.
The Python checks had 25 passes and one skipped Kotlin delivery test,
which requires a separate export receipt. The Q7 wrapper ran both frozen
profiles twice and matched all 14,160 rows with zero tolerated score
differences. Temporary replay outputs were removed.
Independent long-context scoring and physical Fold acceptance remain
open.

### 2026-11-24 hysteresis across context retention

A controller regression with more than 1,500 typed characters reproduced
an early window cut. The first request chose a bounded prefix. By the
next late-local request, the context store had evicted older characters.
The previous implementation dropped one additional word from the model
prefix, even though the previous window plus the newly typed word still
fit the 256-byte budget. The pre-fix test failed on prefix equality.

The store now counts evicted UTF-16 units at whole-grapheme boundaries.
The model window uses that offset and verifies the overlapping text
before reusing its start. Late local scoring takes the offset from the
same pre-space snapshot as the text. The tests verify the continued
prefix and the reset of the offset when a context snapshot is restored.

All 1,417 app and 19 runtime JVM tests passed without skips. The Gradle
log SHA-256 is `60624e55bcef2a6bd2e90ff19e302b5a546578f8b25a1be8c8c8776a7b34d54d`.
A2 request parity passed on all 12,000 rows, with 1,877 calibration and
2,004 holdout requests matching exactly. The receipt SHA-256 is
`070be71a7d00ae17fccb7cb42ec7b360bc10e2e2c5e591a9febeeb8372215cb2`.
Both frozen Q7 profiles matched all 14,160 rows with zero tolerated
score differences. The JVM scenario verifies stable controller input.
Live cache measurements and independent long-context qualification for
this change remain open. Temporary outputs were removed.

## Host model score comparison: incomplete

`a2_score_parity.py` sends the matched holdout request streams to two separate
instances of the pinned host scorer and compares the complete numeric results,
excluding only duration. All 2,004 responses matched: 1,996 contained equal
scores and eight returned `SCORING_FAILED` in both processes. The command exited
1 with `MODEL_ERRORS_RETAINED`; its receipt is explicitly `INCOMPLETE`. An
earlier diagnostic run stopped at the first shared error (ordinal 49). The
full receipt and numeric-only outputs are under
`build/review-a2-score-parity-full-20261028/`.

These are two host scorer processes on the same ordered requests; this does not
establish historical bitwise replay parity, full controller outcome parity,
or Android native behavior. No error was retried
or discarded, and no A2 qualification or feature enablement follows from this.

### Failure-site observation

A separate host diagnostic copy of `scoring.cpp` adds a fixed numeric marker to
each direct `ScoringFailed` return; it does not change the production scorer.
On the same ordered 2,004 requests, its complete responses matched the prior
host run after removing duration. All eight errors reached the first direct
return: at least one candidate's token sequence ends at the longest common
prefix, so the scorer deliberately rejects the set rather than rank a zero
span. This identifies the rejection branch, not which candidate relationship
caused it in each row, and does not establish Android behavior.

The diagnostic files are under `build/review-a2-error-diagnosis-20261028/`.
Original scorer SHA-256 is
`f3e30db8fde25e9fd56ccc3743b70b9304d537b94b44b69e791acc969fc9ee09`,
instrumented source is `c21a9f53ac60c13c2327a82b79df98aef09e4df088d6f906078c4d643b5fb82c`,
and the marker log is `db4555ef01e6a6220b06a9e199a4b123c9d5af019219aa0864cf8d22ec43e5e2`.
The eight rows remain errors in the preceding score comparison; this diagnosis
does not turn that incomplete run into a pass.

## Controller replay with retained model responses

The historical scorer contract explicitly treats a zero divergent span as an
error and the product holdout retains such responses for deterministic fallback
(`NATIVE.md` and `2026-09-03-smart-typing-0.3-product-spelling-holdout.md`).
The eight failures above are therefore contract responses, not missing rows;
the separate score-comparison tool's stricter zero-error gate remains failed.

The 2,004 retained responses were supplied to the same current host controller
JAR in two `ready` runs on all 6,000 holdout rows, with the window off and on.
The existing delivery adapter maps scorer errors to `UNAVAILABLE`; it does not
deliver an Android wire error code. All rows completed and the complete
observations matched after excluding only `fullTokenGenerationNanos` and
`hostStageNanos`, including boundary and Backspace outcomes. No new model calls
were made in this replay. The comparison is at
`build/review-a2-controller-parity-20261028/comparison.json`, SHA-256
`78b7369561b5483e90e279cb4d85e6670eb36bf197ceb56c56b1195c126f7023`;
the response adapter TSV SHA-256 is
`2272ef411046c449a7e1a8e3ab4d525f626ba4216051ca34aa7c61368d73caae`.
This is a revealed historical corpus with current host source and retained
responses, not a bitwise reproduction of the original frozen release, a fresh
long-context qualification, or real Android asynchronous/error behavior.

## 2026-11-24 frozen scorer cache recovery

The original final controller replay archive survives in Git at
`1a5826e12c6ecc036cc0e028c6c44cc927d8375e` under
`tools/eval/smart-typing-0.3/results/2026-09-06-final-controller-replay/`.
The archive binds the pinned model and historical runner SHA-256. A
read-only check verified the archive member digests, decompressed request
and response caches, the export and policy seals, each recalculated cache
identity and both complete score receipts through the original replay
validators. Calibration has 2,983 responses including nine
`SCORING_FAILED`; holdout has 2,973 including fourteen. The uncompressed
score SHA-256 values are respectively
`ce550e89ac17ab71dc949afacb0631f68b718aa0b80d301e947621995561182c`
and `db0bb33c8e745d7d5aeb1f56c3761c34bfaa9cc2ae2d34285db57efd0900ae63`.

A new source-only export at `932027a7482edc0b81afcacef6447d35e2293e71`
compared flag-off and flag-on requests for all 12,000 rows. It again found
identical request streams across those two modes. The request receipt
SHA-256 is `0c4e9d83aab5323b8fc2dbf94937b12ed90ee676e3809341d2485770e8333d3e`.
Each current request was then joined to the archived request by split and
row ID and compared for exact prefix, candidate IDs and ordered candidate
continuations before accepting a historical response.

| Split | Current requests | Exact archived payloads | Exact payloads with historical error | Changed candidate membership |
| --- | ---: | ---: | ---: | ---: |
| Calibration | 1,877 | 1,675 | 3 | 202 |
| Holdout | 2,004 | 1,809 | 8 | 195 |

All current request IDs have a corresponding historical request in the
same split. Every payload difference is in candidate membership, with
candidate IDs also differing in 32 calibration and 27 holdout requests.
There were zero prefix differences. This recovers exact historical
responses for 1,809 current holdout payloads, including the eight
recorded contract errors. The fresh native comparison is recorded below. The 195 changed holdout payloads require
their own scoring and cannot inherit archived scores. No native scorer
or model calls were made in this cache audit.

## 2026-11-24 native replay of the complete archived holdout

The evaluator build definition, scorer and CLI sources and the llama.cpp
gitlink match the archived controller replay revision. A fresh Release
build against clean llama.cpp `36b10154383b60eb15baac2c7a40d2a5f784faa7`
produced runner SHA-256
`ff6f03f3b797911d3ac0da85772e132c47276402f51b33e9c6997639a5c71e8a`;
the original executable SHA-256 is
`bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553`.
A separate fresh build produced the same new executable digest and
passed the CTest math test (1/1). The pinned 396,704,416-byte model
matched the app manifest's SHA-256 before the run. The independent
token-at-a-time native oracle exited zero with that model.

The rebuilt executable received all 2,973 archived holdout requests in
their original order. Every response passed the existing request/response
contract validator. Comparing canonical response JSON after removing
only `durationMillis` yielded 2,959 exact numeric responses, including
all candidate IDs and token counts, and the same 14 `SCORING_FAILED`
responses. The runner and replay exited zero. Both the rebuilt output
and an independent normalization of the archived cache have SHA-256
`2c200c3374ea04b4ae9011e0d2db19df6cc9e9813b2cc6f21b3d1e2c71668e9b`.

The archive run removed its temporary directory.

### Fresh scores with the prefix window off and on

At source `f669286663df6d9223b1a665c21b6a3a9112f5ed`, the source-only
controller export compared both flag states across all 12,000 rows. The
fresh request receipt SHA-256 is
`80615df2151a3077215403fd79a78e2d7d26b5d2f18346d520ffc9f192c9ee54`.
The parity tool scored both emitted holdout streams in separate native
processes using the verified rebuild and model above. All 2,004 responses
matched after excluding duration. Of those, 1,996 have scores and eight
have `SCORING_FAILED`.

Comparison with the archived cache reproduced the same numeric scores
for 1,801 payloads and the same error for eight. All 195 payloads with
changed candidate membership received matching fresh scores in both
flag states. The numeric output SHA-256 is
`af18b03404cede0512c1990e5226d5525234366ac3b733a138fdb7b312bd12e6`.
The strict zero-error gate still reports `INCOMPLETE` with
`MODEL_ERRORS_RETAINED`. The archive comparison confirmed all eight
errors are historical contract outcomes. The replay removed temporary
files. Independent natural long-context qualification and Fold
measurements remain open.

## Android native cache probe attempt on API 37

At clean source `8894162d`, a disposable ARM64 API 37 emulator and the pinned
Rune Text 0.1 model (SHA-256 `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`)
were used for a native cache probe. The debug native build and the existing
probe compilation succeeded. The probe process used CPU but produced no result
after several minutes, so it was deliberately terminated; its shell exit was
143. No reuse counts or score parity were obtained.

A separate `RelWithDebInfo` native build also succeeded. In the disposable
checkout only, the probe build helper's native directory and CMake build-type
checks were changed to select that build; no production source changed. This
probe likewise produced no result within the bounded observation and was
terminated with exit 143. Neither attempt demonstrates a native failure or a
performance bound. The emulator, model and temporary build were removed. A2's
Android native reuse, long-context quality and physical-device acceptance remain
open; these attempts do not authorize enabling the feature.

## Probe progress and optimized-build support

The test-only native probe now emits fixed stage names to stderr before and
after model loading and each warm/cold scoring call. These messages contain no
model path, prefix, candidate or typed text. The Android build helper accepts
both Debug and RelWithDebInfo arm64 directories, verifies the corresponding
CMake build type, and records it in the receipt; other variants remain refused.
This replaces the temporary helper modification in the preceding attempt.

Five Python tests pass. One compiles and runs the real probe against a small
fake scorer and checks all stage transitions, the existing output and a model
load failure; it does not exercise llama or Android. The build-helper test
checks that both accepted variant paths still reject an invalid compiler before
creating output. Two initial test-edit invocations used the wrong working
relative path and failed before editing; the corrected edits and final tests
passed. The instrumented real-model probe was not rerun in this step, so the
location of the prior delay and Android reuse remain unknown. A future device
run still needs an externally enforced time limit and remote-process cleanup.

## Bounded API 37 probe: delay narrowed to common-prefix processing

At clean source `4fd9c51c`, a fresh ARM64 API 37 emulator and the SHA-verified
Rune Text 0.1 model ran the RelWithDebInfo test-only native probe under the
Android toybox `timeout -k 5 120`. Its fixed stage messages showed model loading
completed and the first warm score started, but no completion before the timer
returned exit 124. The executable SHA-256 was
`55e28b27fb35606a33419d2f49af1c00d2699aec953a978a8ac8de54848bf94a`.

A second, 60-second bounded run used a disposable instrumented scorer copy with
four extra fixed labels. It showed tokenization completed and common-prefix
processing began; its completion label was not reached before exit 124. The
observed scorer copy SHA-256 was
`6d70dd0c3eb6a0ff0f1db1f4a897dc72c9e85ef22d50a9c41edad4b828b46b2f`, and the
executable SHA-256 was
`8485b0220092bfc1b777c7b2a915cb9b7b19779773df96dedf726f23622a8740`.
The label precedes the common-prefix loop and its batch setup; it does not
isolate a particular `llama_decode` call. After both timeouts, no probe process
remained. The emulator, model, builds and instrumented copy were removed.

These are observations on a two-core emulator, not proof of a hang, a Fold
performance measurement, JNI behavior, or cache reuse/score parity. No
production source was modified. Android native reuse and A2 qualification
remain open.

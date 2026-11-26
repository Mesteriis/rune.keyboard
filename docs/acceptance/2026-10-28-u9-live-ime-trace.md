# U9: cold IME and emoji trace on API 26

This is a diagnostic series, not acceptance of the first-open or presentation
budget. On an isolated ARM64 Android 8.0/API 26 emulator with 2 GiB configured
RAM, the release-shrunk, non-debuggable profile IME was used with a separately
packaged debug QA editor in another process. The five samples switched to the
system IME, force-stopped Rune's profile process and confirmed its PID absent,
started atrace, selected Rune, then sent an ADB tap to Symbols and an ADB tap to
Emoji. The editor contained no typed text. The filesystem cache was warm and
package speed compilation had succeeded.

Each trace has one framework start-process marker and one instance of every
listed Rune trace section. Perfetto v58.2 reported no nonzero importer errors or
data-loss statistics. Durations are wall-clock trace-section durations, not
CPU time or a touch-to-presented-frame measurement. Nested sections overlap and
must not be summed.

| Trace section | Five samples, ms | Median, ms |
| --- | --- | ---: |
| Cold `createInputView` | 6.424, 2.040, 3.029, 8.408, 2.545 | 3.029 |
| First `emojiConstruct` | 0.860, 0.530, 0.711, 1.038, 1.001 | 0.860 |
| First `emojiTabs` | 2.205, 2.746, 1.923, 1.453, 1.719 | 1.923 |
| Nested `emojiCatalogRead` | 1.953, 2.449, 1.646, 1.229, 1.490 | 1.646 |
| First `emojiGlyphFilter` | 0.548, 0.404, 0.590, 0.370, 0.426 | 0.426 |

Profile-process PSS measured roughly five seconds after selecting Rune was
29,896, 30,048, 29,676, 29,381 and 32,044 KiB. This is a whole-process snapshot,
not the memory cost of the emoji panel or a comparison to a no-emoji build.

The traces show the opening code ran in all five attempts. **Correction:** the
original version of this receipt wrongly described attempts 2, 4 and 5 as black
based on the image preview. A later direct examination of the original PNG pixel
bytes established that all five 1080×610 keyboard-area crops are identical to
the populated grid visible in attempt 1 (SHA-256
`b92f102b1bdf473dd60a5ee47606b91752e2d504434ef4f7eb8747de9ad48211`).
The later screenshot and the one after an additional tap have that same crop
hash. The prior black-frame and recovery assertions were incorrect. The emulator
graphics log contains EGL/SurfaceFlinger errors, but this series does not
establish their effect. All samples are retained; neither the opening budget nor
a physical-device result is claimed.
The original local `results.json` retains its incorrect screenshot labels;
`pixel-correction.json` supersedes only those labels, not the trace/PSS values.

Source: `fc23d27bb90cb2bf5ce84134527c2e9ccddc73f7`. Profile APK SHA-256:
`5ba876ef07c0bf30f3d2fc74f3fb18ae1fe5a8376eefb0b46cacc704bd36f3a4`;
qualification editor APK SHA-256:
`3f105837204155ce5a2332dfefda431230c400f27773af77b9e178704d29d3d2`.
Both installed APKs matched the built bytes. The command
`:app:assembleProfile :app:assembleDebug -PruneNativeQualification=true --offline`
passed. Traces, screenshots, per-sample memory output and analysis script are
retained under `build/review-u9-live-ime-20261028/`. The task-owned emulator
was stopped; the physical Fold was not used.

U9 remains open for a valid touch-to-presented-frame measurement, baseline comparison, Fold displays and
manual TalkBack. This series cannot establish that cold IME startup did not grow.
The [subsequent same-emulator follow-up](2026-10-28-u9-black-frame-followup.md)
records the pixel-byte correction and a further controlled series.

## Same-emulator cold-path comparison

The pre-emoji parent `6086e257` and current source `f5108055` were built as
separate non-debuggable profile APKs from clean temporary checkouts with the
same pinned native submodule. One isolated API 26 ARM64 emulator was configured
with 2 GiB RAM. The independent debug qualification editor contained no typed
text. Six cold process starts of each profile were interleaved in the fixed
order B,C,C,B,B,C,C,B,B,C,C,B; before each, the system IME was selected, the
profile APK was reinstalled and speed-compiled, and its process was force
stopped. Each trace contained exactly one matching system `Start proc` marker
and one complete `Rune#createInputView` section for the observed process; the
ftrace buffer reported equal entries recorded and written. This equality is
not a full Perfetto importer or data-loss validation.

| Measurement | Before emoji, six samples | Current, six samples |
| --- | --- | --- |
| System process-start marker to input-view creation end, ms | 40.930, 35.376, 31.657, 19.720, 27.556, 33.774; median 32.716 | 21.014, 35.587, 28.316, 14.692, 39.488, 27.773; median 28.045 |
| `createInputView` section, ms | 1.625, 1.629, 3.081, 2.176, 2.430, 4.478; median 2.303 | 1.730, 2.591, 3.962, 1.540, 1.572, 2.834; median 2.161 |
| Process PSS after approximately four seconds, KiB | 101257, 102580, 101706, 103335, 102297, 102136; median 102216.5 | 18847, 17722, 18379, 18761, 19446, 19549; median 18804 |

The ranges overlap for both timings, the sample is small, and the two commits
include many other changes. These observations do not attribute the PSS or
timing difference to emoji, measure first touch-to-presented-frame latency, or
prove that cold startup cannot regress on Fold or another device. Actual
display presentation, opening budget and physical-device acceptance remain
open. APK SHA-256 values were `5765840b3af45ed9b8862ed44e10ed51b79ce96eff0b35d3f56e9a0ccfb29ce2`
for the baseline and `5c84a445ecc940aed13db5ac4bdbbdf77cd06486ee761dad2fff3b8f40285b28`
for the current build. Raw traces, PSS snapshots, individual command exit codes
and numerical analysis are retained locally under
`build/ci-editing-investigation/u9-cold-start-comparison`.

The same twelve `dumpsys meminfo` snapshots were subsequently decomposed by
their reported PSS categories. Median `.apk mmap` was 86,817.5 KiB for the
baseline and 2,601.5 KiB for the current build; median native heap PSS was
4,885 and 4,849.5 KiB, respectively. The `.apk mmap` difference accounts for
most of the difference in total process PSS in this series. The
[earlier controlled U17 study](2026-10-27-u17-profile-startup.md) separately
identified eager packed-asset page access and verified lazy reading with
asset-identical builds. The present U9 comparison uses different commits and
does not itself identify which mapped files or changes caused the difference.
The snapshot hashes and all category values are retained in
`u9-cold-start-comparison/memory-breakdown.json`.

After all samples and identity metadata were saved, the orchestration process
exited with a Python `TypeError` in its cleanup call. Its `finally` block had
already stopped the owned emulator and the temporary directory was removed;
the isolated ADB server was then stopped separately. No listener remained on
ports 5039, 5574 or 5575 and no owned emulator process was found. No phone was
used and the locally built APKs were removed with the temporary checkouts.

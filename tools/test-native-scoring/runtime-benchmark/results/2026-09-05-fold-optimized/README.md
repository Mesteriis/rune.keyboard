# Fold optimized runtime measurements, 2026-09-05

Source: `10e894e8dc9e7bc05e2bce0c826059ec6e53b3c9`.
Physical Fold SM-F966B, Android/API36, authorized `phone` profile and exactly one
authorized USB device. The release instrumentation APK was installed without
clearing data. Its installed ARM64 native hashes matched the proof, which in
turn matches both native libraries byte for byte to the app release APK.
The ordinary keyboard installation is the separately optimized **Debug** APK;
do not relabel these library release measurements as a full IME run.

Exact model: 396704416 bytes, SHA-256
`7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`.
The test independently verified the complete digest before native construction.
This warms filesystem cache: the measured load is a new runtime/model lifetime,
not cold-storage access. Existing public fixtures, candidate sets, visit order
and profile counts were unchanged. No text was generated or read from an editor.

Pilot completed 27 measured requests plus nine warmups. The subsequent explicit
full profile completed 180 measured requests, **20 per configuration**, plus
nine warmups. The table uses full-profile request wall time in milliseconds:

| Language | Candidates | p50 | p95 | Max |
| --- | ---: | ---: | ---: | ---: |
| EN | 2 | 74.641 | 80.729 | 130.756 |
| EN | 4 | 34.850 | 74.848 | 86.465 |
| EN | 8 | 103.098 | 148.276 | 182.899 |
| RU | 2 | 226.398 | 239.986 | 260.530 |
| RU | 4 | 190.009 | 260.200 | 300.370 |
| RU | 8 | 297.989 | 400.282 | 429.061 |
| ES | 2 | 122.792 | 134.026 | 136.949 |
| ES | 4 | 124.528 | 172.555 | 197.532 |
| ES | 8 | 219.046 | 295.415 | 300.311 |

Percentiles are nearest-rank descriptive statistics of this fixed schedule,
not population confidence bounds. Repeated calls share a persistent context/KV
cache. The two/four/eight comparisons include different common token prefixes
and cache histories; a larger candidate set need not be slower in every cell.
They are not independently cold requests or an ablation of one optimization.

Full-profile construction/load/unload/close wall observations: 3.145 / 340.020 /
74.168 / 0.139 ms. Load process CPU: 338 ms. All three cancellation attempts
returned CANCELLED; no completion race. Maximum observed signal-to-end time:
0.946 ms. Admission does not prove cancellation inside a particular tokenizer
stage. The following recovery request succeeded.

Maximum sampled PSS/RSS: 472.345 / 555.867 MiB. These are snapshots, not peaks or
leak measurements. The unrestricted benchmark consumed 116.503 process CPU
seconds over 38.770 wall seconds, including its control/validation overhead.
It intentionally does not use the production duty worker. Continuous scoring
at this benchmark rate is therefore unsuitable as a typing/battery policy;
production admission, cancellation and idle unload require separate measurement.

The phone was charging over USB at 13–14%, battery temperature 35.6–35.7 C,
thermal status 1 before/after the full run. It was locked during these native
measurements. There was no concurrent project build/test/benchmark. This is not
an unplugged energy test, a no-throttling claim or a controlled thermal study.
The `rune_ime_selected` numeric flag was false and later corroborated by Rune's
onboarding UI showing the keyboard disabled; the runtime test does not need an IME.

The archived CSV, summaries, native proof, content-free conditions and manifest
are sufficient for exact reaggregation using `protocol.py summary`. Commands:

```sh
./gradlew -PruneRuntimeTestBuildType=release :runtime-llama:assembleReleaseAndroidTest :app:assembleRelease
python3 tools/test-native-scoring/runtime-benchmark/native_proof.py \
  --build release \
  --test-apk runtime-llama/build/outputs/apk/androidTest/release/runtime-llama-release-androidTest.apk \
  --app-release-apk app/build/outputs/apk/release/app-release-unsigned.apk \
  --output build/smart-typing-0.3/fold-optimized-release-native-proof.json
python3 tools/test-native-scoring/runtime-benchmark/run.py --profile pilot \
  --proof build/smart-typing-0.3/fold-optimized-release-native-proof.json \
  --rows build/smart-typing-0.3/fold-optimized-release-pilot.csv \
  --summary build/smart-typing-0.3/fold-optimized-release-pilot-summary.json
python3 tools/test-native-scoring/runtime-benchmark/run.py --profile full \
  --proof build/smart-typing-0.3/fold-optimized-release-native-proof.json \
  --rows build/smart-typing-0.3/fold-optimized-release-full.csv \
  --summary build/smart-typing-0.3/fold-optimized-release-full-summary.json
```

The runner requires exactly one authorized USB target, reviewed/installed APKs
and an existing private exact model. Repeats require fresh output names. No
historical 13.6-second unoptimized Debug result is treated as this build's latency.

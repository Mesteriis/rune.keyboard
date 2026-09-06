# Complete current app matrix — API26 and API37

Commit `6f7c35eda1ee11a9f0a510eadadd0fbf2912356c`. Both full ordinary app instrumentation runs completed the same161 distinct cases:158 PASS,3 explicit optional-model assumptions, zero failures. API26 took1329.455s; API37 took1267.787s. Exact full logs, commands, source/APK hashes and per-case status parsing are retained. Every bound source and APK hash was checked again after completion and remained identical.

The three assumptions on each platform are the explicit opt-in installed-model scorer, service and typing probes. No opt-in flags were provided in the ordinary matrix. They remain assumptions, not silently counted PASS. A separate exact-GGUF public Android runtime test passed on both platforms and is archived under `tools/test-native-scoring/results/2026-09-06-emulator-real-runtime`; it does not relabel these three app probes.

The complete matrix includes the actual resident contextual strip tests, late Space expiry/allowed grace/next-text invalidation, editor/language changes, held Delete, process death, composing rejection/drop handling, sensitive-policy counters, independent diagnostics consent/capture exclusions and settings/key identity. Per-case results are in results.json. All failed earlier fixture runs remain in their original archives.

The postcommit JVM receipt binds743/743 tests with zero failures/errors/skips. The240-task prescribed local gate log belongs to the same frozen source delta immediately before the commit. Independent final integration review found no demonstrated blocking code defect; it expressly leaves physical, external CI and release acceptance open. The later named-example audit independently records missing retrieval targets and cannot be overridden by a green technical matrix.

No phone was used. These results do not complete physical Fold transitions, editor diversity, rapid-input frames/event loss/energy or formal model qualification. Version stays0.2.0 and main merge is not claimed.

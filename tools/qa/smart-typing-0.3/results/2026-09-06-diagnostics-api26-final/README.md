# Complete API26 rerun after the reviewed preview target wait

149 PASS +3 optional-full-model assumptions, zero failures across152 cases;
1171.451s. All five diagnostic settings/editor tests pass. The original preview
failure and both isolated changed-case passes remain in the sibling
`2026-09-06-diagnostics-reviewed-matrix/` archive. Its base receipt/source copies
plus this exact test delta bind the tested sources; product APK is unchanged.

This is the completed required full API26 matrix. It is separate from the later
phone-only opt-in admission-triage test APK and does not prove real-model phone
quality. Numeric status bundles without class/test are excluded from case counts.

JNI command history: an initially overbroad runtime runner invoked8 cases, yielding6 PASS and2 missing-full-model fixture failures. The explicitly scoped ordinary `LlamaRuntimeInstrumentedTest` then passes6/6 in0.054s. The original8-case output is retained; no real-model API26 PASS is claimed.

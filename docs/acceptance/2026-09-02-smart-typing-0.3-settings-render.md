# Smart Typing 0.3 — settings rendering, 2026-09-02

Baseline: `83837fd3e4a6b6fc8da5d5bc5eeae63b09de1ab7`. Nonvisual settings previously called `renderKeyboard()`, which replaced key children immediately or queued their replacement until touch release. Avoiding input-view recreation alone did not preserve keys.

The service now retains three paths: theme/geometry/preview recreate the view; enabled-language changes render keys; all other cached settings update only candidates. Existing policy/Undo invalidation stays intact. No new settings consumer, model binding or automatic spelling correction is added.

The strengthened existing mechanical test holds a real key, changes the setting, checks keyboard/key object identity before release, then checks it again after UP and queue drain. It also verifies exact next-input output, immediate Undo and six zero editor-readback counters. Test-only window inspection uses guarded WindowInspector on API29+ and legacy reflection below it. Inspection failures fail the test on the instrumentation thread; no screenshots, external window trees or view-text diagnostics are collected.

Proposal SHA-256 `696ac86b08315bb1efb03112ee54e16db7703dee010af9e8ba3422e055a84e4a`; independent review `4c632a7577086e6857962f14c59b71f5047191fe8e7942fbcbe363d6cdeac6c9`, no P1/P2 findings. Source compilation and isolated patch dry-run passed. Parent verified the exact source identities and separately applied tests before production.

Old-service control on API37: **1 test,1 failure**,12.887 s. The post-release assertion reported `Key instance changed at index 0`. This is an executed regression control, not merely a prediction from source. Its failure is preserved separately.

Fixed actual Binder mechanical class: **API26 3/3 PASS**,34.884 s; **API37 3/3 PASS**,39.874 s. All six terminal test statuses succeeded. These are functional durations, not latency measurements. Full prescribed lint/build/privacy/dependency/native gates plus Android test assembly: **PASS**,267 tasks/46 executed (`build/smart-typing-0.3/settings-render-gates.log`). Required fresh post-commit JVM verification is recorded in the execution ledger with the resulting commit SHA.

Logs, metrics and source/built-APK identities: `tools/qa/smart-typing-0.3/results/2026-09-02-settings-render/`. Both AVDs received the recorded final APK pair via successful install-r operations. APK hashes are build identities, not installed-APK readback attestations.

Physical Fold: **BLOCKED**, USB readiness still returns no device; no physical install/test for this fix. API27/28 and remote CI: **UNRUN**. This closes the scoped key-rebuild defect, not full Smart Typing settings, quality, device, performance or release acceptance. Version remains 0.2.0; no push or publication.

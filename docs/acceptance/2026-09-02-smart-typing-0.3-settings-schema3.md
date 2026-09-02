# Smart Typing 0.3 — settings persistence, 2026-09-02

Schema3 persistence prerequisite; UI and Smart Typing consumers are separate integration work. A stored preference is not effective model availability or approval of automatic replacement.

The immutable settings snapshot now carries independent autocorrection (`OFF`, `SUGGESTIONS`, `HIGH_CONFIDENCE`), mechanical punctuation, contextual punctuation (`OFF`, `SUGGESTIONS`) and candidate-strip preferences. Fresh/legacy defaults are `HIGH_CONFIDENCE`, true, `SUGGESTIONS`, true. These fields do not require key-view recreation. No editor text or model payload is persisted; decoding never consults model state or writes preferences.

| Input | Result |
| --- | --- |
| Absent schema or Int1/2; absent new field | Approved default |
| Present malformed individual preference | Only that preference falls to OFF/false, including existing double-space |
| Int3 with missing preference | Missing field falls to OFF/false |
| Malformed/unsupported schema | Effective Smart Typing and double-space fall to OFF/false; ordinary settings preserve existing policy |
| Explicit writer on supported/repairable schema | One editor transaction normalizes safe known values, stamps3, then applies the explicit choice |
| Valid future Int>3 | Writes preserve version and all unrelated raw data; the selected key is stored, but effective Smart Typing remains unavailable to this older reader |

All existing writers participate in migration. Snapshot, normalization and apply are serialized on the shared `SharedPreferences` instance across cooperating facades, preventing a stale migration snapshot from re-enabling an independent disabled preference. This does not promise coordination with arbitrary external direct writes or cross-process SharedPreferences.

Reviewed proposal: `7e5b784a5aab6462df83107ba1cb743b055b6d9dfba7c93998c8c615e560717a`, five source/test paths. Independent review found no P1/P2 issue in persistence scope. The author compiled actual project settings code and ran29 focused JVM tests, including15 new cases. Removing only the synchronization reproduced exactly the intended stale-write regression, with28 other tests passing. This control is evidence about the regression, not a supported implementation.

Root integration: `./gradlew testDebugUnitTest --rerun-tasks` PASS468/468, zero failures/errors/skips;46 tasks executed. Log: `build/smart-typing-0.3/settings-v3-jvm-integrated.log`.

Full prescribed command (`lint assembleDebug assembleRelease assembleProfile privacyGateRelease privacyGateProfile imeIntelligenceBoundary forbiddenRuntimeDependencies :runtime-llama:nativeSymbolGate`) PASS:238 tasks,45 executed. Log: `build/smart-typing-0.3/settings-v3-gates.log`.

Actual Android disk/restart migration, settings UI, immediate consumer updates, full API26/API37/Fold matrix and release hardening are not qualified by these JVM tests. Version remains0.2.0; no remote CI, push or release is implied.

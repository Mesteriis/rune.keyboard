# Q4 — application/Undo clean-source release regression

Committed `7073366` passes privacyGateRelease and apkFootprint from a separate
clean checkout (exit 0). Its unsigned release APK is 180,100,681 bytes.
The preceding application-undo receipt binds 1,322 JVM tests, four actual API 26
methods and a fresh 15,288-row current-source replay with exact non-timing parity.
This release gate is a regression check, not an independent proof that no text
can ever be recorded; typed API, numeric codec and origin/persistence regressions
provide their separately scoped evidence.

All 13 original owner tracked changes and 98 original untracked paths remain
preserved; none was copied into the clean release checkout. No owner installation,
public release/push or independent F-Droid build-server proof is claimed. The
owned Q4 emulator is retained for remaining Q4 integration; instrumentation is
complete, synthetic metrics were reset and IME/preferences restored by the driver.

Q4 remains open for kept-original/window-expiry outcomes, real model duration,
unavailable/CPU copy, debug-only export, final device integration and two actual
weeks of owner use. The complete review remains open; the observation period is
not represented as having started from synthetic fixtures.

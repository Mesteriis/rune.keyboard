# Q4 — source dashboard and real atomic storage checks

The existing quality dashboard now shows all 14 fixed source rows, each with
applied / explicit Undo / kept-original / expired-application-window counts.
Explicit Undo fraction is shown only at 100 source applications; insufficient
or inconsistent data is identified. This is observation, not correction
accuracy or an automatic source-disable policy. A separate five-bucket model
response section retains the existing six candidate-response buckets.

Three actual API 26 instrumentation methods pass with zero skips. Synthetic
fixtures show 100 applications / five explicit Undos / one original kept / one
window expiry for common confusion and 99 applications for joint short words.
They verify 5% versus insufficient-data reporting, all five model timing bins,
Activity recreation, the actual reset button, all source rows reset to zero and
a durable empty v3 disk snapshot. The second method instantiates the real private
AtomicQualityStorage on a temporary emulator-only file: a v2 fixture migrates
without invented source/model history, and the full 1,149-byte v3 maximum payload
writes/reads through actual Android AtomicFile beyond the previous 1,024-byte
cap. The third method checks EN/RU resource tables and localized numeric format.

Store-mutating methods reject hardware outside ranchu/goldfish and require the
explicit owned-emulator marker before accessing files or resetting the global
store. The temporary atomic-store files are deleted with checked results.
No owner profile is imported, no Fold command is used and all numbers are
synthetic fixtures; this is not a natural typing or field-accuracy observation.

Initial lint rejected a quantity string as PluralsCandidate. Both locale strings
were rewritten with the quantity label before the numbers; no check was
suppressed. The final debug APK/test APK builds and debug lint pass. Main/test
APK hashes, source identities, raw failure and successful logs are bound by the
adjacent evidence. The foundation's 1,313 JVM / 31 quality tests and profile
privacy check remain their own source-bound receipt.

Q4 remains open: source/outcome hooks on acknowledged editor actions, exact Undo
and window attribution, real model elapsedMillis, unavailable/CPU copy, debug-only
export, renewed replay/release/device integration and two actual weeks of owner
use still require completion. The dashboard fixtures do not establish those
hooks. No owner installation or start of that observation period is claimed.

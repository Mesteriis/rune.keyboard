# U5: visible confirmed words and individual removal

Dictionary and learning → Personalization now opens Confirmed words. The list is
available even when personal learning is off, shows word/language and a bounded
count, and filters by word or language. Native ListView rows are reused rather
than inflating all 512 entries. Filter text uses NPL+NO_SUGGESTIONS and does not
turn learning on. EN/RU/ES resources and an unexported activity are included.
The intro explicitly includes dictionary words; origin tags are not invented.

`recordConfirmedWord` reports success/refusal, accepts an existing confirmation
even at capacity, and never exceeds 512. Individual removal affects only the
normalized word/language confirmation. Pair rejections and phrase records remain;
phrase suggestions recheck spelling, so a removed non-dictionary confirmation
stops approving that word for phrase output. A serial PersonalTypingStore method
saves the removal and reports actual write success. Failed writes keep the RAM
intent, display an explicit failure and offer idempotent retry; unsaved removals
may return after restart. The profile format and phrase-only import are unchanged.
No PERSONAL retrieval pool, confirmation export or merged stores were added.

Original, accepted-correction and validated manual-retype confirmation paths
share a once-per-full-table-episode notice. Invalid words and existing approvals
do not produce a false full warning. Protection actions now distinguish invalid/
full, not-ready and IO-failure messages, retaining the separate protected-word
switch and storage.

Validation:

- All 1,195 app JVM tests pass without failures/errors/skips. Four new model
  tests cover capacity results, duplicates, freed capacity, language isolation,
  pair retention, phrase eligibility and unchanged codec round-trips. The new
  capacity-result regression first fails on old code (12 tests, one failure).
- Five instrumented scenarios pass with explicit synthetic opt-in on a fresh
  Android 36 arm64 emulator: actual Original confirmation appears in the list;
  deletion and pair rejection survive an explicit host force-stop/new process;
  full-table callbacks fire once and a real Toast accessibility notification is
  observed; injected write failure preserves old file bytes and explicit retry
  persists removal; the actual settings row opens the new screen. Rows expose a
  word/language action, filtering and recreation are exercised. The restart phase
  verifies a changed process ID and exact profile SHA before decoding it again.
- The fault/capacity fixtures refuse physical hardware and require
  `runeSyntheticProfileFixture=true`; the scoped host runner also rejects skips.
  No Fold or owner data was used. The disposable emulator was stopped/deleted.
- Final IME boundary, release privacy, debug lint and debug/test APK builds pass.
  Early builds failed on a handler outside lexical scope; using the existing
  main-Looper idiom fixed that. A navigation test used Activity instead of the
  decor View for tag lookup and was corrected. The first Toast assertion used
  the UI tree; the passing test observes its actual accessibility event.
- All 12,000 frozen ordinary product observations/metrics are unchanged after
  excluding host timing fields. This replay does not load private personal data
  or exercise the new UI/store: model/JVM and instrumented tests prove U5.
  Existing EN gate limitations and the ES holdout false change remain separate.

USER_GUIDE, PRIVACY and architecture describe individual removal, retained vetoes
and phrase evidence, capacity and save failure. Exact commands, identities and
outcomes are adjacent. This is local/emulator acceptance, not physical Fold or
complete-review acceptance.

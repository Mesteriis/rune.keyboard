# U8 — unknown left context after service recreation (partial)

ExternalEditContinuity previously required an in-memory flag plus a matching
framework restart. A new Rune service had no flag, although its editor could
still contain pasted text. The first output-only probe passed hide/show and
service rebind, but final text alone did not establish that the guard existed.
A stronger native assertion confirmed a different actual service instance, an
enabled typing session and a missing external-boundary flag. That old-code run
failed before typing the suffix; it did not capture an incorrect replacement.
The earlier output-only pass is retained as insufficient guard evidence.

onStartInput now passes both numeric selection endpoints to the continuity
policy. Whenever their minimum is greater than zero, the new session requires
new Rune whitespace before adopting a composing word or correction context.
This recovers protection without any old service state or editor-text read.
The parameters are required, so a caller cannot silently assume an empty field.
Existing same-editor restart protection still applies to its RAM flag. A zero
left endpoint or invalid negative position does not invent preceding text.
Controller eligibility continues to reject unsupported/invalid editor contexts.

This is intentionally conservative: on a new connection with preceding unknown
text, the first typed suffix stays literal even if that preceding text happens
to end in whitespace. Rune cannot inspect it to prove that boundary. A newly
inserted Rune Space/newline restores ordinary correction for the following word.
Fresh empty fields and replacement selections starting at zero retain their old
startup behavior. No persistent state, typing history or package acquisition was
added. The user guide and privacy copy explain this choice.

Validation:

- 1,230 JVM tests pass, zero failures/errors/skips. Four new policy cases cover
  fresh/restarting positive positions including Int.MAX_VALUE, unknown package/
  field identities, forward/reversed selections, zero/negative endpoints and
  refusal to adopt a previous session's own whitespace as a new boundary.
- IME/scoring boundary, release privacy, debug lint and debug/test builds pass.
- Twenty-five final Android 36 arm64 cases pass in bounded groups: eight public
  panel/lifecycle cases, six former ownership/restart/detach regressions, seven
  WebView/Compose/preview cases, and four suggestion-flag/search cases with their
  positive-control model Binder observers. The new stronger cold case checks
  the actual new service's guard before typing, no composing/context adoption
  of the adjacent suffix, literal final text and correction after Rune Space.
- Hide/show retains absolute zero counts for all six payload APIs. The real
  service-rebind test explicitly switches through another enabled IME, which
  may read its editor. Its transition counts are not attributed to Rune and
  are not reset; the test takes a settled baseline and asserts no additional
  payload API calls during subsequent Rune typing. Other editing cases retain
  their absolute zero-read assertions. No zero-read claim is made for the
  fallback-IME transition itself.
- The original weak two-case probe passed; the strengthened old-code probe
  failed once on the missing guard; the corrected focused pair and all final
  groups pass. These outcomes are retained separately.
- The ordinary 12,000-row replay is reused by exact current identities of all
  88 compilation sources, 18 runtime assets and its driver. Those source/asset
  identities were also verified before the production edit. The changed service
  and continuity policy are outside that harness: the new startup behavior is
  covered by the policy/native cases above, not by a claimed fresh replay.
  Existing EN precision/volume limitations and the ES holdout aggregate false
  change remain; this is not full release qualification.
- The task-owned emulator was stopped/deleted. No Fold effects or installation.

U8 remains open for physical Fold, manual TalkBack and remaining lifecycle scope.
This evidence is one real service recreation while instrumentation remains alive,
not an Android process-death test. At a cold zero-offset start, numeric selection
cannot establish whether unknown text remains to the right (for example after
Cut at the beginning); this change does not infer it or provide a persisted
handoff. Framework metadata is not universal logical editor identity. Exact
source/APK/log/result bindings and replay-reuse scope are in the adjacent JSON.

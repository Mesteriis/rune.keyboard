# Rune 0.3.1 dogfood autocorrection diagnostic

Date: 2026-09-12. The source capture is private and ignored under
`build/dogfood/2026-09-12/`; no typed text or conversation context is committed.
`SHA256SUMS` verifies all eight rotated diagnostic files, package/input-method
state, preferences, Logcat snapshots, and the installed APK.

The bounded rotations contain 11,723 text-stream events and 3,306 metadata-stream
events. The text stream includes 347 session-start records and 497 word-boundary
decisions. The final-outcome analyzer found seven word autocorrection attempts:
six remained applied and one was undone. It also found 33 mechanical edits, five
of which were undone. This is low autocorrection coverage, not evidence that the
user made few corrections.

The installed schema did not record Backspace as an input event. A conservative
private reconstruction found at least 57 suffix-deletion runs covering 150 UTF-16
characters; 37 runs occurred while a word was being composed. This is a lower
bound because only exact retained-prefix transitions were counted. The new
`BACKSPACE` event removes this ambiguity for subsequent captures; the analyzer
does not reinterpret old revision gaps as exact presses.

The raw boundary counts overstated readiness failures. Of 103
`RESULT_NOT_READY` records, 62 followed a valid-word result plus a contextual
punctuation request. Another 129 `NO_RANKING` records were valid words. These
paths required no spelling correction. The controller now reports `VALID_WORD`
before inspecting spelling ranking, so contextual punctuation cannot masquerade
as a missed spelling decision.

All twelve recorded model `scoringCode=15` inputs were replayed with the exact
qualified GGUF (`7a97111c…`) and the native `rune-score` executable. Eleven
reproduced `INSUFFICIENT_CONTEXT` at document start and one reproduced
`SCORING_FAILED`; none reproduced as a successful score. Android deliberately
maps both native outcomes to stable wire code 15, so diagnostics now classify
that code as `SCORING_FAILED` instead of the broader `MODEL_ERROR`.

The capture also contains 27 successful model responses that conservatively
abstained, 11 model-service refusals, and seven accepted model rankings. These
figures explain inconsistent coverage but do not justify lowering the frozen
quality threshold or enabling the general local policy, whose independent 99%
qualification remains failed. The patch changes attribution and future evidence;
it does not claim broader autocorrection coverage.

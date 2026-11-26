# Q5 authored deletion boundary diagnostics

The 19 previously disclosed synthetic deletion phrases were replayed with the
existing metadata-only boundary observer. Two runs matched byte for byte and,
after removing diagnostic metadata, all 19 observations matched the earlier
non-diagnostic replay. The observer never requests diagnostic text.

Of 12 unchanged final words, four received `TOO_SHORT` (`молоо`, `сдау`,
`заняо`, `подошл`), three `SEARCH_INCOMPLETE` (`мето`, `двох`, `собй`), three
`ORIGINAL_VALID` (`пакт`, `кара`, `привези`), one `WINNER_AMBIGUOUS`
(`следующй`) and one `INSUFFICIENT_MARGIN` (`растительне`). The seven applied
corrections were attributed to local policy (six) and contextual ranker (one).
The event reflects the emitted boundary refusal; it does not prove that an
intended candidate was generated or explain why a search was incomplete.

For Russian, the qualified general-local ranking uses minimum length seven;
the shorter words can still enter separately qualified paths. Candidate search
completeness and existing-word protection are safety boundaries, so these
observations alone do not justify weakening them. The [numeric receipt](2026-10-29-q5-authored-typo-diagnostics.json)
binds the raw replay and analyzer; the companion replay receipt binds inputs,
assets and registries. The analyzer tests reject missing or inconsistent events
and wrong target outputs. CI runs the same diagnostic replay. This disclosed,
synthetic sample is not a natural quality estimate or a new qualification;
Q5 and the changes requiring independent holdouts remain open.

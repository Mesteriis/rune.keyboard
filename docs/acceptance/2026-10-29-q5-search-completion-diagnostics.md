# Q5 boundary search-completion diagnostics

At a `SEARCH_INCOMPLETE` boundary refusal, the existing technical diagnostic
record now carries the available local-search completion and numeric state and
terminal counts from the controller's accepted candidate generation. Existing
reason codes, candidate and admission decisions, editor operations and schema
are unchanged. An absent selection leaves `NONE` and zero counts. No extra
text is requested. `UNAVAILABLE` describes missing complete evidence and by
itself does not distinguish an intentionally skipped search from an unavailable
resource.

The token observer on the three previously disclosed four-letter cases showed
an unavailable local search with zero counters, while ordinary candidate search
completed. `двоих` and `собой` appeared among ordinary suggestions; `метро`
was not in the displayed three for `мето`. This separate token observer starts
with a prefilled prefix and does not establish complete full-session candidate
coverage. The current generator deliberately skips its general-local pass for
fewer than five code points. None of this qualifies a new automatic policy.

A direct reason-code change was tried first and refused by the frozen 2,160-row
replay: 60 rows changed only the recorded boundary reason. That attempt was
reverted. With the compatible completion fields instead, the two-pass frozen
2,160 and 12,000-row projections both match exactly. All 1,391 app JVM tests
passed without skips; focused tests exercise both `UNAVAILABLE` and
`STATES_EXHAUSTED` with their counters, unchanged typed text and zero editor
text reads. The initial release privacy gate refused the dirty source tree and
is not counted as a pass. Local replay and test logs are under
`build/q5-search-completion-*`; the ongoing API 37 general run uses an older APK.
The actual device update and physical acceptance remain open.

After commit `91a8205b`, the clean-source offline `:app:privacyGateRelease`
passed, including release diagnostics packaging. The raw log is
`build/q5-search-completion-privacy-clean-20261029.log`.

# U11: completed local search before broader budget exhaustion

The preceding English candidate screen found 165 constructed deletion or
transposition inputs whose full-token search ended `STATES_EXHAUSTED`. In all
165, the product observation reports that the preceding local radius-one
search completed. Its recorded full local alternatives contain the original
frequency-list surface in 139 cases; that surface is the only local alternative
in 132, and is first in 135. It is absent from the local alternatives in 26.

| Disclosed synthetic slice | Deletion | Transposition |
| --- | ---: | ---: |
| Wider search exhausted; local search complete | 73 | 92 |
| Source surface in local alternatives | 64 | 75 |
| Source surface is only local alternative | 58 | 74 |
| Source surface is first among local alternatives | 61 | 74 |
| Source surface has at least one competitor | 6 | 1 |
| Source surface absent from local alternatives | 9 | 17 |

This identifies a possible narrower source for EN experiments. A completed
radius-one pool does not certify the broader radius-two candidate order, and a
frequency-list source surface is not a verified intended correction. The
synthetic contexts are not natural sentences; no control accuracy, false-change
rate, actual user intent or model quality is established. Existing completion,
valid-word, personal, admission and qualification vetoes are not changed.
The result does not authorize a replacement on an exhausted broad search.

The screen reuses the source and replay alignment validation from the
[candidate-pool diagnostic](2026-11-03-u11-english-candidate-ceiling.md), whose
fresh 2,160-row current-product replay matched its frozen projection. Two
independent screen outputs were byte-identical. The [numeric receipt](2026-11-03-u11-english-local-search.json)
SHA-256 is `70f899f77caab60c3e23246af91d005c14686f5a1631f2fb55e9cad95c9f026d`.
Three tests cover unique versus competing candidates, incomplete local pools
and malformed observations. The screen is wired into CI; hosted CI was not
run. No model, threshold, product code or APK changed. U11, Q6 and Q7 remain open.

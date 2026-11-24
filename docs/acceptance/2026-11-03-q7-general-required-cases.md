# Q7: required general-suite regression cases

The general Android CI report previously required at least 300 reported and
250 executed cases but did not require specific identities. A filtered run
could meet both floors while omitting an earlier failed scenario. The report
gate now also requires eight previously failed editor-boundary, neighbor
recovery and mechanical-punctuation methods to be present and executed without
failure or skip. Existing suite floors, separate fixture scopes, failure checks
and device guard remain in force. This is a targeted minimum, not a claim that
all other scenarios are present.

The 13 host-side suite-runner tests pass, including explicit missing and skipped
required-case mutations. Actual retained successful API 26 and API 37 general
JUnit reports pass the new identity gate (352 and 353 reported cases,
respectively, each with 48 skips). Mutating one required case to skipped in each
real report causes the new check to reject it. No emulator was run for this
report-parser change. Hosted CI still has not run the current changes; the
latest published workflow remains the earlier failed run at `2c1ff975`.

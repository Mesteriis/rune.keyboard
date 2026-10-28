# Q2: current guide facts

This scoped documentation/tooling slice follows `d912a69`. Q2 remains in progress;
full provenance and README path closure are outstanding.

The Russian guide and diagnostic reference now identify writer schema 9 and
known analyzer formats 1–9. They distinguish the finite WORD_CONTEXT rules from
CONTEXTUAL_RANKER and grammar revision sources. EDITOR_ACCEPTED is a command
response; actual editor text needs an independent oracle.

The guide separates manual ranking context (48 characters, 320216-byte
ru-ranking-context.bin plus 22036-byte ru-ranker.bin) from the 24-character,
81848-byte ru-context.bin tap model. Stale historical quality figures are no
longer presented as current product qualification. The acceptance index points
to the current review map while retaining historical reports.

`python tools/check_guide_facts.py` checks these bounded facts against the feature
registry, diagnostics writer, model constants and actual asset sizes. It does
not validate every sentence or model quality. CI invokes it in the stdlib job.

Validation: all 10 guide mutation tests pass on Python 3.12.14 and 3.14.6.
Learning-disclosure and typing-source documentation gates pass; CI YAML parses;
`git diff --check` passes. Hosted CI was not run. No production code, asset or
APK input changed, so the prior Fold installation was not repeated for this
slice.

Only the reviewed guide changes were staged: unrelated pending guide additions
remain outside this commit. The pending diagnostic-source paragraph was
intentionally corrected against shipped source; its original bytes and the
original pending guide were preserved under ignored local build evidence.

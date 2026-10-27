# Q6: applied-word template history and v8/v9 group reuse

Verified the original applied-role generator snapshot and its later revision,
then reproduced the two sorted JSONL payloads byte for byte: 32,852 and 33,428
rows. Both extend the already registered 31,916-row v7 corpus exactly, adding
936 and 1,512 template rows respectively. The older snapshot's form sorting and
comparative-form filtering differ from the current generator; the current file
is not substituted for the earlier frozen version. Archived both generators
and the common preparation script. Preparation scripts are not executed.

Corpus selection receipts match manifest hashes and actual group-file
hashes/counts (31,448 and 32,024). Every embedded selected row equals the
reproduced source row. v8 and v9 group files also match v7 group bytes exactly;
their selection references and training-plan hashes/counts agree. These are
30,512 reused groups per version, not new independent examples. Hash agreement
and row lineage do not establish that a model fit executed or reproduce models.

Dictionary-only candidate analyses yield 59 families in the first corpus and
60 in the second. The additional reading честной was absent from default
supervised/prepared-family exclusions. It is now conservatively quarantined,
along with 379 previously unblocked left-context/target keys. Unknown corrupted
inputs are not assigned guessed canonical lemmas. Source captures, labels and
data identity do not qualify the examples as fresh evaluation.

Added four durable family/context entries, preserving all previous 99 entries
and incomplete global coverage. Their bindings retain the verified parent,
archived generators, preparation source, corpus manifests/rows, selected groups
and reuse evidence. Both versions overlap extensively; exposure and unique-ID
counts are recorded separately in the adjacent evidence JSON.

All 181 tests pass in a fresh source-only directory without original corpora,
models or morphology packages. Both registry schemas validate with incomplete
coverage. New regressions check exact parent extension, selected-row labels,
copied-group bytes, reuse-plan consistency, archive identities and alternative
full-adjective lemmas. Snapshot/real preparation CLI tests preserve the new
честной exclusion: exit code 2 and no output directory. CI includes these tests;
no remote CI run is claimed. The dictionary-backed audit exits 0 without model
calls. Original archived-source differences are expected and are not a failed
corpus reproduction.

Full review closure is not claimed. Q6 still needs later input/residual chains,
unsupported lexical families and the outstanding origin/source gaps described
in the preceding receipts. No source admission, runtime model, APK or phone
change was made.

# Q6 historical neighbor-prefix compound exclusions

The 15,000 retained neighbor rows disclose 2,500 distinct article/prefix
frames in 2,426 articles. Both source audits checked every frame against the
exact seven pinned Wikipedia shards; three frames have multiple exact source
matches. Complete interior compound and mixed-script tokens in those frames
produce 268 occurrences of 232 distinct forms, of which 192 were not already
in the preceding control ledger. Matching archived text does not establish
that a model learned any particular token: these are conservative exclusions.

The control ledger now excludes those exact forms and their observed contexts;
the lexical ledger excludes the observed contexts, 262 of which were new to
the preceding ledger. Existing dictionary-only
family and unresolved-fragment protections remain in place, and no new lemma
is inferred. Tokens touching an uncertain prefix edge, including a dangling
hyphen whose continuation falls outside the prefix, are omitted. One such
case caused the first audit to fail and motivated a boundary regression test.

Two source audits and two registrations were byte-identical. The retained
context and receipt SHA-256 values are respectively
`4355db6aaaeb8db28694489335206e067ff534fc8c4c26e3afea646afffd2171` and
`3f68f4924c4c9587270d4eea62fb3fa7ae6dc196d239629277e1e303178c140c`.
The receipt's new-form count is relative to the pre-registration ledger.
Static verification checks the complete projection against the hash-pinned
historical frames and binds the source-audit receipt and analyzer; it does not
rerun the seven source-shard scans. The original historical generator and full
independent-data coverage remain unresolved; this is not model qualification.
No model, application, or APK was changed.

Validation passed: six focused tests and the registration check in a staged
source archive without `build/`; the previous neighbor and truncated-source
registration checks; 24 public-ledger snapshot tests, 10 control-ledger tests,
12 holdout-ledger tests, and seven test-inventory runner tests. The complete
stdlib profile and hosted CI were not rerun for this slice. Task-created audit,
registration, and staged-source directories were removed after verification.

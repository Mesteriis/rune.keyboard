# Q6: partial EWT annotated-lemma exclusions

The disclosed pinned English EWT source supplies exact annotated lemmas. Two
separate source-verified extractions produced byte-identical exclusions: 10,485
distinct normalized lemma keys are present in the pinned public FrequencyWords
vocabulary. The existing EWT parent entry and all three source partitions are
verified before extraction; the new entry preserves existing ledger entries and
its incomplete-coverage status. The stored keys are unsalted hashes of public
vocabulary words, reversible by dictionary attack, and are not anonymization.
No source text, document identifiers, or token-level associations are added.

Of 254,820 integer-token rows, 212,277 matched that public vocabulary; 4,587
recognized-shape lemmas fell outside it and 37,956 token lemmas had unsupported
shapes (including punctuation and numbers). The 3,370 non-integer CoNLL-U rows
are separately counted. Exact annotation identity is not proof of correct or
complete English word-family analysis; other spellings and inflections are not
inferred. The filter protects against publishing hashes of arbitrary source
strings but leaves real gaps.

Preflight can screen explicitly supplied `englishLemmas` under the independent
`new-families` profile. A match blocks overlap, and malformed labels fail closed.
English qualification stays unsupported even without a match; caller-provided
labels are not independently verified. The `new-sentences` profile retains its
existing historical-family semantics. Q6 remains open, as do complete lexical
coverage and independent corpus/model qualification. No runtime policy changes.

Validation: the extraction was repeated twice with identical output. The
clean-source archive passed the 25 preparation tests, four exclusion tests and
registry check without a `build/` directory. Historical text-boundary checks
passed. The stdlib inventory ran 171 modules: 170 passed and the isolated
no-build test failed because its explicit copy list omitted the new helper. That
copy list was updated and the affected test then passed on its own; the full
inventory was not repeated after this test-only fix. The inventory check and
English key tests also passed. These are local checks, not a hosted CI run.

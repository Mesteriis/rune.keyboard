# Q6: dictionary families of disclosed Q7 regression surfaces

Both already-disclosed Q7 corpora were reconstructed and their existing ledger
parents verified before examining Russian surface forms. The screen takes the
exact Cyrillic lexical surfaces already disclosed by each registration: typed
tokens, source target/context tokens, and, for original v2, candidate and
whitespace-delimited prefix tokens. Mixed-script, punctuation-bearing and other
nonlexical strings are not assigned lemmas by this step; their original control
and surface exclusions remain in force.

| Disclosed set | Distinct lexical surfaces | Dictionary-resolved | Unresolved exact surfaces | Distinct lemma keys |
| --- | ---: | ---: | ---: | ---: |
| Q7 product v1 | 1,076 | 690 | 386 | 745 |
| Original spelling v2 | 3,266 | 597 | 2,669 | 459 |

The pinned dictionary-only analyzer contributes **all** analyses for each
resolved surface, including ambiguous alternatives. Unresolved words, many of
which are artificial misspellings, are stored as exact surface exclusions;
no canonical family is guessed for them. These are disclosed regression data,
not supervised training and not an independent qualification. Original
context/surface entries and global incomplete coverage remain unchanged.

`import_q7_regression_families.py` binds the original corpus inputs, generator,
ledger parents, dictionary package receipt and all relevant source hashes.
Two runs produced byte-identical ledger and receipt. Receipt:
`build/review-q6-q7-family-exclusions-final-20261028/receipt.json`, SHA-256
`82bc3801b063dc83cb071c98736fd52a6d8101130f5a0064229c26501b732a1e`.
The focused test checks ambiguous union, unknown surface handling, case
normalization and rejection of non-string inputs. No model was run.

The first stdlib inventory run failed a snapshot test that assumed a fixed count
of unsupported-surface entries. The test now verifies both new entries
separately while retaining the earlier 13-entry and historical-key assertions.
The corrected full inventory passed 758 tests across 151 modules with no skips.

## Authored typo-target coverage

The original Russian spelling corpus has 1,930 typo-labelled rows whose typed
form is not recognized by the pinned dictionary (1,929 distinct typed surfaces).
Every one has an explicit authored `expectedSpelling` recognized by that
dictionary, and all dictionary analyses of those targets are already represented
in the original-v2 family addendum. Thus no target family key was missing for
these rows. This is a relationship supplied by the disclosed synthetic corpus,
not a linguistic analysis of the misspelled surface or evidence of user intent.
Other unresolved surfaces and the overall family-coverage gap remain open.

`audit_q7_authored_typo_families.py` rechecks the original corpus identity,
ledger parent, pinned dictionary receipt and current ledger; it refuses missing
target family keys. Two runs matched byte for byte. Receipt:
`build/review-q6-q7-typo-family-audit-20261028/receipt.json`, SHA-256
`9d9e9d563bfe66c5b59f2413b4bbb3a1aaf70716f5d42a6d2f8ca941a72e05ad`.

## Q7 v1 source-variant coverage

The v1 generator supplies four deterministic transformations per source group;
it expressly does not label the variants as correct words or actual errors.
All source/variant relations were revalidated against the original generator.
Among Russian rows, 373 variants (346 distinct surfaces) are not recognized by
the dictionary. In 280 rows the source form is recognized and all its dictionary
family keys are already in the v1 addendum. In the remaining 93 rows, the source
form is itself unrecognized (26 distinct surfaces); each is already an exact
surface exclusion. Neither case establishes a lemma for an unknown variant or
claims the source word is linguistically correct.

`audit_q7_variant_families.py` validates the frozen corpus, ledger parent,
dictionary receipt and every generated relation, and fails on missing family or
unknown-source surface keys. Two final runs produced identical receipts:
`build/review-q6-q7-variant-family-audit-20261028/receipt.json`, SHA-256
`0cfb5a3298d1c4ef2acf68be2ff2747ea7d56cbdbe48e91c746cce878fd5d2e0`.
An initial script and unit-test run failed because the generator function was
looked up in the registration module; the import was corrected before both
final runs. The focused test covers relation drift and missing family detection.

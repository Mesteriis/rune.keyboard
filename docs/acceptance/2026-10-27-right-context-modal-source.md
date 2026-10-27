# Modal/copula conflict evidence without changing ranking

Source-v6 prevents one wrong diagnostic proposal after `могло быть`, with all
136 previously useful proposals preserved. It only rejects conflicting edits;
it does not select the correct alternative, expand target parts or qualify a
deployment. Installed assets and Fold remain unchanged.

## Bounded evidence and refusal priority

`right_context_modal_source.py` wraps the unchanged source-v5. Every previous
pre-scoring decision and refusal retains priority. Only after source-v5 would
allow the already ranked proposal does it inspect a narrow completed left chain:
an adjacent past finite form of `мочь`/`смочь`, followed by infinitive `быть` and
trailing whitespace. Every dictionary reading of both tokens must support those
roles; the modal must have known singular/plural number. No guess or target
label supplies a dictionary reading.

The chain is restricted to the existing 128-character/eight-complete-word clause
window, with whitespace only between its two tokens and after `быть`. No comma,
newline, identifier, unfinished token, intervening adverb/negation or other verb
is skipped. An explicit cut-edge check prevents a hidden identifier prefix from
manufacturing an apparent modal token. Boundaries before a complete chain may
start its own clause. Present/ambiguous `может быть` is not covered by this rule.

The existing agreement helper refuses number or gender only when all available
readings establish a conflict. Compatible ambiguous readings and missing gender
do not create a universal gender veto. The source does not decide that the modal
must be correct and the following subject wrong: conflicting evidence simply
cannot justify an automatic replacement under this certificate.

No scores, pool members, order, margin, thresholds or original-word protections
change. No runner-up is substituted. Source-v5's grammar-neutral lemma-change
guard still runs first. Pure PRTS targets remain outside the inherited source's
admission contract; this slice does not silently broaden it.

## Fixed-model actual diagnostic

The unchanged v14 composite manifest is
`8fdbd315a7db9238ef4feb2cf98b58db835beb23ea136c5f7400f9639f5e3365`.
The same 7,905 disclosed calibration records, 739 scored pools and 1,752 actual
continuation events are rescored. The independent comparison verifies identical
trace keys and every score/order/margin/expected-rank field. Old vetoes are
unchanged. Each new path is exactly the old path with the new vetoed step removed.

There is one new gender veto and one changed accepted path: a feminine proposal
after the real dictionary's unambiguous neuter past modal. The stored reference
is also neuter. The wrong feminine proposal is removed; the unknown original
stays in place because the source does not rerank or grant the reference form.
No correct accepted path is lost and no unrelated path changes.

| Source | Correct proposals | Wrong proposals | Prior-correct losses | Control changes |
| --- | ---: | ---: | ---: | ---: |
| v5 | 136 | 10 | 0 | 0 |
| v6 | 136 | 9 | 0 | 0 |

These are first positive-margin source-certified diagnostic proposals, not a
selected-policy precision or independent test result. Raw proposal precision is
136/145 (93.79%), below the user's 95% floor. The unchanged 33-point threshold
fit still fails minimum-100/zero-new-wrong requirements, natural cohort volume
is still insufficient and no holdout is scored.

## Checks and next work

All 194 default `test_right_context*.py` tests pass. Four new tests cover compatible
feminine/neuter/plural chains, conflicting number/gender, ambiguous/missing
analyses, present/non-modal verbs, punctuation/identifier/window boundaries,
completed-token requirements and preservation of prior vetoes and preconditions.
Real-dictionary inspection, full diagnostic scoring and fixed-model/trace/path
audit complete successfully. Quality and corpus-volume gates remain failed.

Next is explicit short-participle and modal/infinitive role supervision and
admission evidence, including valid repairs and competing non-predicate roles.
The current veto prevents an unsupported change but does not prove or implement
the intended correction. Disclosed failure text remains diagnostic; do not use
it as new supervision or add a lexical blacklist to hide errors.

This is host-only source work. No JVM, lint, APK, installation, on-device
dictionary parity or following-input editor ownership/cancellation/Undo check
is claimed. Artifacts under `build/right-context-v14-source6-traced-20261027/`
and their identities are bound by the accompanying evidence receipt.

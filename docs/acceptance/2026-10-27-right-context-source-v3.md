# Continuation source-v3 and exact decision attribution

An experimental source now uses completed continuation timing and independent
finite-copula number evidence. Existing source-v2, frozen feature layouts, model
weights and application assets remain unchanged. This is an offline source
experiment, not an installed correction policy or editor-ownership certificate.

## Source changes and preserved protections

`ContinuationSourceScope` delegates all common source checks to source-v2. Only
the final `CONTRADICTORY_RIGHT_NUMBER_CUE` and
`NO_SUPPORTED_RIGHT_NUMBER_CUE` interpretations can be reconsidered after those
checks pass. Unknown/explicit-original protection, initial ownership, complete
retrieval, whole-pool comparison, external veto, spelling cost/kind, independent
morphology certificates and an unambiguous short-predicate target remain
mandatory. Existing right-gender conflicts are not overridden.

The new interpretation can use an immediately adjacent left finite copula or a
completed right copula before/after the apparent subject. Each observed finite
copula must support the proposed number and must not contradict gender. A
plural `были` can therefore support a plural predicate before a list that starts
with a singular noun; the first noun does not independently veto it. A comma
after the left copula breaks adjacency.

Without independent copula evidence, a bare nominal waits for an actual strong
clause boundary. Pending commas/nominal links, an unanchored reciprocal and an
ordinary finite verb after the apparent subject have distinct refusal reasons.
Identifier/window boundaries are not closure. A closed potential nominal list
permits both possible plural and nearest-subject patterns rather than forcing
plural universally, including for `или`. These are admissible interpretations
for an experimental scorer, not proof of contextual intent or qualification.

No target is injected into retrieval. Unchanged/protected/invalid proposals are
still refused by the original source checks before grammatical reconsideration.
Nine new tests include differential common-veto checks and specific number,
gender, timing, reciprocal, finite-role and boundary cases.

## Trace fidelity and copula regressions

The same 7,905 disclosed calibration records were replayed with v6/source-v2,
v8/source-v2 and v8/source-v3. Every scored prefix records the actual winner,
score/margin, expected candidate rank/score, top five candidates and exact source
refusal. Expected labels are used only for diagnostic reporting after ranking.

The v6/source-v2 and v8/source-v2 accepted paths match their prior diagnostic
artifacts exactly: instrumentation changes no proposal, score, margin or timing.
For all three runs, accepted traces exactly match accepted path steps, rejected
traces cannot appear as accepted steps, and every accepted step has a trace.
The comparison also requires identical original, prior output, expected word,
control flag, full suffix and context group across the three datasets.

Aggregate matched-copula gains/losses concealed a useful distinction: changing
v6 to v8 loses 22 previous correct first source-certified proposals and gains 10,
for a net loss of 12. At the exact old action prefix, all 22 losses are the new
ranker retaining the previous output. Source-v2 did not reject a correctly
ranked expected candidate in those cases. All ten gains likewise occur where
the old ranker retained the previous output. This is model interference, not a
reason to weaken the source checks.

## Fixed-model source comparison

Holding the v8 model and pools fixed isolates the source change:

| Context group | Source-v2 correct / wrong | Source-v3 correct / wrong |
| --- | ---: | ---: |
| Matched copula | 40 / 0 | 40 / 0 |
| Direct subject | 75 / 1 | 53 / 1 |
| Agreement-role negative | 1 / 23 | 46 / 13 |
| Other-part hard negative | 0 / 29 | 0 / 22 |
| Other-part ordinary negative | 0 / 0 | 0 / 0 |

These are **first unthresholded source-certified diagnostic proposals**, not
accepted policy precision or on-device edits. Correct proposals total 116 →
139 and wrong proposals total 53 → 36. Nineteen old wrong paths are removed,
two new wrong paths appear, and 34 remain wrong. The two introduced wrong paths
belong to the hard other-part and direct-subject groups, one each. A net count
alone is not sufficient to call the source qualified.

All 45 additional correct paths were previously rejected specifically with
`CONTRADICTORY_RIGHT_NUMBER_CUE`: 31 now have adjacent-left-copula support and
14 have a completed nominal link. There are also 22 lost direct-subject correct
paths. Replaying their preconditions at the exact old action gives 17
`NOMINAL_CONTINUATION_INCOMPLETE`, four `NOMINAL_LINK_INCOMPLETE` and one
`FOLLOWING_FINITE_ROLE_UNRESOLVED`.

Recovery is separately audited rather than inferred from that first refusal.
Twelve of those lost paths have no later eligible prefix in the bounded window.
Three later retain the previous output. Seven later rank another candidate and
the source correctly refuses its contradictory number; the expected candidate
is rank two in six and rank three in one. Those seven source refusals must not
be loosened as if the expected word had won.

## Qualification and next work

All three diagnostic threshold fits fail the unchanged minimum-100/zero-wrong
requirements. Full cohort availability also still fails; no independent holdout
was read or scored and no policy was selected or activated. The new source
uses the same initial native ownership evidence as source-v2; it does not prove
ownership after actual subsequent editor input. Cancellation and Undo remain
unqualified for this experiment.

The next learning change should preserve useful existing ranking while learning
continuation-dependent adjustments, rather than forcing one new fit to relearn
all candidate ranking and retention. The exact retained-word copula losses and
later wrong-candidate refusals above are the evidence for that investigation.
Nominal cases with no later eligible prefix still require a timing/role strategy;
they cannot be declared solved by waiting indefinitely or shrinking the accepted
scope. No further blind epoch or blanket grammar-veto removal is justified.

## Checks

All 129 `test_right_context*.py` tests pass, including the nine new source tests.
All three diagnostic scorer processes and both attribution audits exit zero.
Trace fidelity and unchanged source-v2 paths pass. Model feature-source hashes,
public replay inputs and installed asset hashes are checked by the scorers.
Quality and corpus gates fail as stated. No Android/JVM code changed; JVM tests,
lint, APK build, installation and device acceptance were not rerun.

The [evidence receipt](2026-10-27-right-context-source-v3-evidence.json) binds the
new source/tests, three traces, source-bound plans, comparisons, refusal recovery,
raw test output and all failed qualification outcomes.

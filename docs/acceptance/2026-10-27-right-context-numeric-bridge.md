# Complete numeric bridge, unchanged baseline and calibration diagnosis

The experimental 178-feature model can now be evaluated by Kotlin using the
same installed feature inputs as Python. It remains unregistered in the running
keyboard. No model, policy or supplemental dictionary was added to application
assets, no APK was installed, and no on-device quality claim is made.

## Explicit numeric layout and compatibility

`RightContextRevisionFeatures` preserves the layout of 146 installed features,
16 frozen-v1 following-context features, one applied-word flag and 15 role
features. It accepts bounded Russian tokens, preserves base-array ownership,
and rejects invalid words, wrong dimensions and nonfinite input. NFC/case
normalization applies to the applied-word comparison; frozen feature semantics
are otherwise preserved, including their distinct raw-candidate behavior.
The model's v1 features are separate from source-v2 admission evidence.

`ContextualRanker` now exposes its actual immutable-index feature calculation
for candidates and the original. Its current score path uses that same
calculation, keeping existing readiness/language checks and score transformation.
`RightContextRanker` composes these inputs and applies the frozen experimental
weights and bounded tanh transform. It supplies numeric scores only, without
editor ownership, source admission or model-registration authority.

The tree decoder allows 178 only when explicitly requested. Existing default
and 146-feature loaders retain exact header matching; unsupported dimensions
are still rejected. The whitelist uses its own numeric schema constant so old
minimal replay builds do not have to link optional feature extractors. Model
magic, size, tree count/depth, index bounds, finite/bounded weights, trailing
bytes and input-vector checks remain enforced. Default/current loaders reject
the new model. Runtime resource fingerprints and qualification are still needed
before any manager could register it.

## Python/Kotlin and baseline evidence

The frozen v6 binary remains 39,444 bytes, SHA256
`dfdc98954e702b3787118cb88ecd3268b25b4b1f498b45777872dc4c4c977594`.
The authored references test:

- 36 controlled-base compositions: every one of 178 fields and the raw tree
  score matches Python exactly.
- 36 complete installed-input cases: candidate, fallback and original metadata,
  full word-pair/grammar dictionaries, character-context model and exact past
  dictionary. Base/revision fields agree within 1e-12; raw tree scores match
  exactly and Python bounded scores agree within 1e-12.
- 284 numeric probes around every one of the model's 71 distinct split borders:
  exact border, float32 predecessor/successor and a double-only increment that
  must round back to the border. All raw scores match at zero tolerance.

Malformed model and vector tests exercise the new dimension explicitly. Getter
ownership/readiness tests cover shared feature indices across secondary weights
without shared mutable vectors. The new scorer rejects unavailable context,
English candidates and wrong-layout weights; these tests are not source-quality
or editor-transaction acceptance.

A freshly compiled current-controller harness replayed all 1,007 existing
label-blind training queries. Every old semantic observation matched the prior
source-bound observations exactly, including scores/candidates/admission/editor
commands/text/Undo. Only `hostStageNanos` and `fullTokenGenerationNanos` were
excluded. The replay contains no experimental right-model activation.

The first minimal-harness compile exposed an optional-extractor dependency from
the decoder; moving the numeric schema constant into the decoder fixed that
coupling. A retry into the existing exclusive-output directory failed before
compilation, preserving the old log. The fresh-directory compile and semantic
replay then passed. Those earlier attempts are retained as failures.

## Corrected corpus audit and duplicate exclusion

The overlapping-pair/per-group collector completed its ten-shard run over
926,220 articles. It now retains 400 genuine direct-subject contexts per part,
but only 75 calibration / 72 holdout matched-copula contexts, below the unchanged
400-per-part requirement. The full cohort gate therefore failed. No successful
corpus/production qualification is inferred from the increase in useful examples.

An explicit diagnostic dataset was then derived from the available records,
without weakening that gate. The identity audit found two old source-context
hashes in different holdout articles. `exclude_prior_contexts` removes *all*
variants of those source contexts before any model scoring; predictions and
expected spellings do not choose removals. The original failed audit and source
snapshot are retained. The filtered identity audit passes with zero prior
article/context, training-family, family-partition or cross-part overlap.

The available diagnostic data has 7,905 calibration rows over 1,661 contexts and
7,750 unscored holdout rows over 1,630 contexts. Matched-copula availability is
75/70 after the ten duplicate-context variants are removed. Correct, protected,
correct-rival and unfinished-input controls retain their declared construction.
The full corpus gate remains false; this is not a qualified substitute corpus.

## Actual calibration findings, not another blind epoch

The current controller replayed all 7,905 calibration rows. The unchanged v6
model and source-v2 first-accepted-prefix protocol were then scored against
these available calibration records only. The declared minimum of 100 new
correct changes with zero new wrong/correct/control losses did not fit. No
candidate policy was frozen, and the experimental model did not score holdout.

Before thresholds, the first source-certified changes are:

| Context group | First correct | First wrong |
| --- | ---: | ---: |
| Matched copula | 52 | 0 |
| Direct subject | 236 | 2 |
| Agreement-role negative | 0 | 138 |
| Other-part hard negative | 0 | 25 |
| Other-part ordinary negative | 0 | 1 |

These are unthresholded diagnostics, not deployable behavior. A separate volume
probe that explicitly does *not* change qualification finds only five new correct
changes at zero new wrong/losses on the declared grid. It is not an accepted
five-change policy.

The high-confidence errors reveal missing structural/temporal evidence. Examples
include plural `возможны` before a subject list beginning `тошнота, …` or
`покупка …`, reciprocal `внимательны друг другу`, and the adverbial use of
`непреднамеренно он …`. The model interprets the first following nominal as a
simple subject and may choose singular too early. Its frozen extractor also
stops at commas and does not represent later coordination/finite-verb roles;
left-past features encode gender but not the decisive plural cue in `были`.
Dictionary POS alone does not establish the contextual role of an adverb-shaped
surface. These errors cannot be repaired by declaring score parity or simply
accepting a lower threshold.

Next work is to model completed continuation/coordination, reciprocal and finite
verb cues, appropriate deferral before the first edit, and preceding finite
number. Source admission must retain those ambiguities rather than grant a
subject from one possible reading. Data coverage still needs replenishment;
new role features and policy require a fresh, explicitly bound evaluation before
runtime ownership, cancellation, Undo and Fold acceptance.

## Checks

All 1,144 debug JVM tests pass (122 suites, zero failures/errors/skips), and
`:app:lintDebug` passes. All 97 right-context Python tests and two past-export
tests pass. Baseline noninterference over 1,007 queries passes. The filtered
sentence-identity audit passes; model calibration and full cohort availability
**fail**, as reported above. `git diff --check` passes. APK build, installation
and device acceptance were not run.

The [evidence receipt](2026-10-27-right-context-numeric-bridge-evidence.json)
binds sources, test data, immutable JVM/lint copies, compile/replay, duplicate
exclusion, identity audit and calibration/volume outcomes.

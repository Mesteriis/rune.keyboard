# Reliable-source Kotlin parity and unbiased sentence collection

This milestone ports source-v2 cue evidence to Kotlin and repairs two data
selection defects. It does not activate the experimental model or change editor
admission on the phone.

## Source-v2 cue parity

`ReliableRightContextGrammarFeatures` composes the existing v1 extractor with a
nominal-cue view. If a surface has PREP, CONJ or PRCL analyses, its noun/pronoun
homographs do not establish a subject. Raw dictionary analyses, known-word
protection and the separate frozen-model v1 features are unchanged. Genuine
copulas, ordinary noun case alternatives and unambiguous personal pronouns
retain their evidence. A function word after a finite copula adds no imaginary
subject while the copula still supplies its own number evidence.

The Python exporter freezes 5,510 authored suffix/candidate cases. All 16 fields
match Kotlin exactly with both the mini fixture and full application grammar:
176,320 comparisons at zero tolerance. Tests also verify raw dictionary and v1
vector preservation, unfinished suffixes and copula/subject distinctions. Data
is dictionary-derived OpenCorpora CC BY-SA 3.0 with receipts and attribution;
it is in JVM test resources and contains no owner text or training labels.

This is component parity, not full Android source-policy or model integration.
The 178-feature model is still unregistered; the existing tree decoder whitelist
and resource binding do not yet provide a production path for that layout.
Private multiword ownership, deadlines, cancellation, Undo and preservation of
following text remain required before on-device activation.

## New-sentence identity audit

`audit_new_sentences` verifies exact source hashes and complete variant groups
before any model scoring. It checks the typo, unfinished-input retention control,
correct word, protected word and optional correct rival against one source
anchor; validates labels/flags/prefix/suffix consistency; and rejects malformed
or incomplete records. It detects an old source phrase even if it appears in a
different article. It reports training-family, old-article/context, fixed-family
partition and cross-part overlap. Prior family exposure is reported without
claiming the legacy metadata covers every earlier occurrence.

Previously evaluated families may appear in genuinely new sentences under the
[explicit new-sentence protocol](2026-10-27-right-context-role-kotlin.md).
Actual supervised families remain excluded and a family cannot cross the new
calibration/holdout partition. This identity audit does not qualify model quality
or silently lower cohort-size requirements. Its prepared runner separately
checks the original cohort counts and family/group/article caps. The runner has
not yet audited a completed corrected corpus in this milestone.

## Two collector defects

The initial ten-shard new-sentence collector completed 926,220 public articles
but retained only five calibration and 23 holdout matched-copula contexts. It
failed the unchanged 400-per-part requirement. Direct-subject counts were
184/132. This failed run and its candidate records remain intact.

Inspection and regression tests identify two independent losses:

- Non-overlapping two-word matches consume `теперь готов`, then miss the adjacent
  `готов был`. The new lookahead traversal visits both pairs with exact original
  capture offsets and preserves word-length/identifier/hyphen/newline bounds.
- Choosing a single globally prioritized case per article discards a positive
  even when it belongs to a different cohort from the selected negative. This
  occurs before per-family caps, so abundant negative examples can starve the
  positive cohorts without adding useful negative diversity.

`choose_article_contexts` assigns each article to one available part using a
fixed, score-blind article hash, then retains one minimum-selection-hash case per
cohort in that part. The caller's family partition remains fixed. It never
inspects predictions, expected spellings or ranker scores. At most five contexts
may now share an article, with at most one per cohort; this correlation is
explicit, not an estimate of natural typing prevalence. Existing group/family
caps and minimum cohort sizes remain unchanged.

The old focused copula collectors reported 19,277 eligible articles before family
caps across their seven source shards. This does not prove the corrected new
corpus is sufficient, but it cautions against interpreting the starved collector
counts as the total available linguistic data.

A separately frozen corrected run is now scanning the same ten hash-locked
shards. It excludes the failed run's bound articles as well, records the new
selection-source hash and article cap before selection, and uses a distinct row
ID namespace. It has not scored a model. Positive/negative availability, exact
sentence novelty and identity audits still precede calibration; a policy must be
frozen before untouched holdout scoring. No success is inferred from a running
collector.

## Verification

The current controller replay harness was recompiled against current sources.
All 1,136 debug JVM tests pass (121 suites, zero failures/errors/skips), and
`:app:lintDebug` passes. All 96 right-context Python tests and two past-index
export tests pass. Source-selection tests include opposite-score inputs so that
following a model score would contradict the expected score-blind selection.
`git diff --check` passes. No Android APK build, phone use, model installation,
or on-device quality/latency check was performed.

The [evidence receipt](2026-10-27-right-context-source-parity-and-selection-evidence.json)
binds source/test resources, immutable copies of the JVM/lint reports, failed
availability and corrected collector plan. Build roots:
`right-context-source-v2-parity-20261027`,
`right-context-current-controller-20261027`,
`right-context-sentence-corpus-v6-20261027`, and
`right-context-sentence-pairs-v2-v6-20261027`.

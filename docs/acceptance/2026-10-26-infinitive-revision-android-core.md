# Infinitive revision: Android core port, not yet connected to the controller

The [offline-qualified component](2026-10-26-infinitive-revision-offline.md)
has a Kotlin implementation of its grammatical restriction and shared-data
scorer. This slice does **not** load new production assets, enable automatic
revisions, alter the frozen general model or update the installed APK.

`InfinitiveRevisionScope` reads the actual packed grammatical dictionary. Every
previous analysis must be finite `VERB`, every proposal analysis must be `INFN`,
and the bounded context must contain the existing infinitive cue. Same-lemma
evidence comes from matching available, present, non-null lemma IDs in the
packaged morphology index. Unavailable or ambiguous lemma evidence declines;
it is not guessed. This is a conservative runtime certificate rather than a
claim that the compact morphology index represents every Pymorphy ambiguity.

`ContextualRanker.withWeights` shares the already validated immutable word-pair
and grammar indices and creates only another numeric tree decoder. It does not
map or copy the dictionaries again. `ExperimentModels` keeps the secondary
scorer separate: it is unavailable until both the installed contextual bundle
and the new weights are ready, returns non-finite scores on unavailable data,
and declines scope checks when unavailable. Invalid secondary bytes clear only
the secondary scorer; reloading the base invalidates its derivative. The
installed score remains independent of secondary weights.

## Checks

Four new scope tests use the full packaged grammatical dictionary, including
real noun/verb and noun/infinitive homonyms. They cover the three disclosed verb
contexts, tabs/punctuation, other intervening words, unavailable/absent/ambiguous
lemma evidence and different lemmas. The scorer test checks missing-base,
invalid-feature-schema and reload states, distinct secondary weights, retention
of the installed score, and positive/negative scope decisions.

The full `:app:testDebugUnitTest` run passed **1,099 tests**, with zero failures,
errors or skipped tests. The 41 Python tests for the offline component also
passed. The host replay source manifest includes the new scope class.

A separately compiled Kotlin/JVM comparator loaded the real mapped indices and
both frozen models:

- **66,645** secondary-model candidate scores matched Python within
  `2.220446049250313e-16`.
- **67,143** installed-model regression scores matched the earlier frozen
  reference within the same maximum error.
- **6,506** scope decisions, under the same existing retrieval/admission
  certificates, matched the Python projection exactly, including all **339**
  eligible revisions across focused calibration, focused holdout and broad
  holdout.

The first scope-input preparation assertion expected 6,507 cases. It stopped
before the Kotlin comparison because one focused calibration input did not
have a complete joint pool: there were 499 scored groups, not 500. The corrected
expectation is derived from frozen source record counts. Original failing
artifacts remain ignored, and the regenerated input is byte-identical; no case
was dropped or relabeled to pass the comparison.

The comparator and logs are ignored under
`build/grammar-revision-android-20261026/`; the adjacent JSON binds the compiler
artifact and aggregate results. These are desktop Kotlin/JVM checks, not device
execution, Android timing or exact editor Undo qualification.

The next integration slice must bind model/policy fingerprints, load the
secondary weights on the resource worker, preserve source admission and current
output outside the qualified scope, dispatch a distinct diagnostic source, and
verify actual controller edits/Undo before a coordinated Fold installation.

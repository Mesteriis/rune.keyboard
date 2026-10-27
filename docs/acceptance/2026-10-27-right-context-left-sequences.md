# Bounded left-sequence inputs and authored exposure

This slice prepares missing training observations; it does not fit or activate a
model. The previous v9/source-v5 and v10/source-v5 natural quality failures remain
unresolved. Android assets and Fold are unchanged.

## Observations

`right_context_left_sequence_features.py` appends 21 fields to the frozen 221-field
layout. The resulting 242-field schema observes the nearest preceding full/short
adjective through dictionary conjunctions, particles and adverbs, including
number/gender agreement, ambiguity and bounded skipped distance. It reuses the
128-character/eight-complete-word clause window. Content words, unknown words,
identifiers and hard clause boundaries stop traversal. Commas can occur within
the observed sequence; the features do not certify syntactic coordination.

Real dictionary inspection found both conjunction and interjection readings for
`и` and `но`. A possible interjection reading is allowed only alongside an actual
conjunction/particle reading, and gets an explicit ambiguity field. A standalone
interjection or an adverb with a noun reading cannot bridge the search. The
existing function-word view continues to suppress letter-name nominal readings.

Other fields expose possible adjacent linking-verb lemmas, applied/candidate
instrumental noun readings and the immediate completed right word's genitive
and nominative-plural alternatives. These are soft dictionary observations,
including missing/ambiguous analyses, not universal grammatical vetoes. The
linking-verb list does not assert that every use of those verbs is a copula.

The old 221 fields are copied unchanged by the new extension. Old model readers,
weights, source policies and Kotlin layouts are not modified. No current model
reader consumes the 242-field profile.

## Authored corpus and actual retrieval

`right_context_left_sequence_corpus.py` reuses the existing dictionary-certified
full/short feminine forms and shared unknown corruptions across all 24 existing
adjective families. It adds six frames: full adjective after an ordinary finite
verb, short predicate after a possible linking verb, and full/short coordination
with conjunction/negation or adversative/degree words. Each frame includes raw
acquisition, retaining the intended applied form, repairing the opposite form,
unfinished-clause retention and correct-original controls. These are explicit
authored training intents, not proof that every natural sentence with the same
POS pattern has only one grammatical reading.

The prepared corpus contains 2,268 rows and 570 label-independent native queries.
All queries complete with the current production replay controller. Selection
retains 1,692 groups from complete joint pools and 576 correct-original controls
from complete manual-retention pools, totalling 24,684 candidate rows. No group
is excluded. Both contrast forms must actually be retrieved for unknown-input
groups; no expected target is injected into candidate retrieval. Applied states
are counterfactual training contrasts, not observed editor actions.

The pinned real-dictionary audit confirms nonzero ordinary-finite/linking exposure
and distinct full/short coordination observations in all six scenarios. All 2,268
actual input tuples are distinct; there are zero contradictory targets. A separate
dictionary smoke check confirms pure instrumental noun/genitive-complement
observations for `был штабом объединения`. That smoke check is **not** supervised
noun coverage or native retrieval evidence for a noun-versus-predicate contrast.

Raw evidence is under `build/right-context-left-sequence-v1-v2-20261027/`, bound by
the accompanying receipt. The earlier `...left-sequence-v1-20261027/` preparation
predates the real-dictionary interjection fix and is superseded; its stale source
bindings must not be used for fitting.

## Checks and remaining work

All 171 `test_right_context*.py` tests pass, including nine new sequence/authoring
tests. Coverage includes both full/short roles, positive repair and retention,
function-word homographs, standalone interjections, content/identifier/clause
boundaries, missing agreement, complete-word/window limits, noun case ambiguity,
normalization, exact append-only layout and invalid feature inputs. Native query
replay, complete-pool selection and real-dictionary exposure audit pass.

No model training, natural quality rescoring, holdout scoring, JVM tests, lint,
APK build, installation or device acceptance is claimed for this slice. The next
missing supervision is pure instrumental nouns after a left copula, with actual
retrieved predicate competitors and genuine predicate-repair controls. Then the
combined inputs need collision/exposure checks and an explicitly versioned model
profile before fitting. The existing quality and corpus-volume requirements
remain unchanged.

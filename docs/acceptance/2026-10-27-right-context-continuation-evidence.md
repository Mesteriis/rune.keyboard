# Bounded continuation evidence and actual decision boundaries

The new experimental continuation extractor appends 24 fields to the frozen
178-field vector, producing a separate 202-field schema. It does not modify
the old extractors, model, admission source, Kotlin decoder or application
assets. No new model was trained, enabled or installed in this slice.

## Structural observations

The scanner consumes at most 128 code points and eight completed Cyrillic words.
It preserves commas, including a trailing comma awaiting another token. Strong
sentence boundaries and identifiers stop traversal; truncation is not closure.
An unfinished word never contributes morphology. The initial separator must
be a space or tab. Commas can precede later list members but cannot establish
an immediate subject before the first word.

Features expose adjacent nominal links with `и`, alternatives with `или`/`либо`,
and comma-separated nominal readings. They do not assert that any such reading
is the syntactic subject or that alternatives require plural agreement.
Finite verbs after the immediate nominal are separate from finite copulas;
commas and adversative conjunctions prevent borrowing a later clause's finite
verb. Function-word nominal homographs use the existing reliable subject view.

Possible reciprocal evidence uses completed `друг`, an optional completed
dictionary preposition, and an oblique dictionary reading of the lemma `друг`.
This includes `друг другу`, `друг друга`, `друг к другу`, and `друг с другом`.
Internal commas preclude this observation. A bare completed `друг` separately
marks a possible unresolved reciprocal; none of these observations establishes
that the surface cannot refer to a friend.

The immediately preceding finite verb supplies number support, conflict and
ambiguity independently of gender. The extractor does not search backwards for
a convenient finite verb or borrow one across a comma. Missing number readings
prevent a universal conflict. Candidate adverb readings remain visible without
declaring their contextual role resolved.

## Timing correction for the next evaluation

The frozen v1 timeline produces decision points only when the completed word
count increases. This misses a comma or strong closure entered after an already
completed word and space. The new `continuation_prefixes` emits those actual
evidence changes at the earliest typed boundary, including when the word count
stays constant. Repeated spaces and unfinished-word characters do not rescore
identical evidence. It stops at the same bounded window and does not synthesize
a delimiter, look at future text, or alter the previous calibration protocol.

## Disclosed calibration diagnostic

The extractor was run on the existing 7,905 disclosed calibration records and
all 454 paths containing an old first source-certified action. Actual preceding
context comes from the hash-bound native replay observations. The original v6
proposals are retained; no new scores, policy or holdout results are produced.

Among the 138 first wrong agreement-role actions, 19 expose an adjacent-left
number conflict already at the old action. Forty-five have a possible bare
`друг` reading; later completed prefixes expose reciprocal evidence in 42.
Later evidence also exposes additive links in nine and comma nominal readings
in seven of these wrong-action paths. Counts overlap and are not repaired-word
counts. Among the 25 hard other-part wrong actions, six later expose a finite
verb after the apparent subject.

Crucially, seven of the 236 correct direct-subject actions also acquire additive
links later, and six acquire a later finite verb. Blanket rejection on these
observations would discard useful changes. This supports conditional role and
timing training rather than treating the new features as admission authority.
Later-prefix evidence is retrospective and cannot be credited to the old first
action. The corpus availability and model-quality gates remain failed.

The final audit is `build/right-context-continuation-evidence-v2-20261027/`.
The earlier directory preserves the first diagnostic before the reciprocal
observation was generalized from two literal phrases to dictionary case roles;
its source hash is historical, not the final extractor hash. Neither directory
contains holdout scores or a deployable policy.

## Checks and outstanding work

All 108 `test_right_context*.py` tests pass, including 11 new tests covering
completed-only evidence, lists, reciprocal roles, finite-clause boundaries,
ambiguous/missing number, source windows, immutable layout extension and
same-word-count decision events. The dictionary-backed audit succeeds against
the existing pinned morphology receipt. No Android/JVM changes were made, and
JVM tests, lint, APK build and device acceptance were not rerun for this slice.

Next steps are authored prefix-by-prefix training that preserves the prior
spelling while the role is unresolved, learning on the new layout, and an
explicit versioned source/timeline integration. The current admission source
still treats an immediate possible nominal as a subject and has no new deferral
policy. Kotlin parity and independent sufficient-volume qualification remain
required before editor ownership, cancellation, Undo and Fold acceptance.

The [evidence receipt](2026-10-27-right-context-continuation-evidence.json)
binds the final extractor, tests, audit and raw test output.

# Contextual punctuation suggestions — 2026-09-03

Baseline `c887e49`. For an ordinary valid RU/EN/ES word preceded by one owned
space and another ordinary word, Rune builds seven bounded continuations:
space, comma, colon, semicolon, period, question mark and exclamation mark.
Sentence-ending alternatives capitalize only the first code point through the
current language locale. Technical, mixed-script, all-caps and otherwise
ambiguous tokens are excluded; Spanish inverted marks remain manual.

The existing 400 ms pause, private Binder client and serial inference worker are
reused. A typo with spelling alternatives receives the one model request for the
word; an exact valid word may instead receive contextual ranking. Rune never
issues both. Replies require exact session, revision, request, candidate IDs and
composition identity. Only a non-space result with average log probability
strictly above the original space is rendered. It remains a suggestion: a tap
replaces only the current Rune-owned composing span and creates no automatic
Undo transaction.

The persisted preference remains independent from effective availability. The
IME activates read-only readiness metadata without dictionary or inference work
while the model is missing. The settings screen probes descriptor readiness off
the main thread and reports Ready separately. No editor readback, payload
persistence, network path, second per-word inference or automatic contextual
edit was added.

Fresh final-source JVM result: **651/651 PASS**, zero failures, errors or skips.
The prescribed lint, debug/release/profile, privacy, dependency, IME boundary,
native symbol and Android test assembly gates pass with **277/277 tasks
executed**. A first concurrent duplicate gate launch caused a shared lint
temporary-file race; that run is retained and is not counted. The clean isolated
rerun passed in 47 seconds.

Real Binder/synthetic-engine instrumentation passes on API 26 and API 37:
**10/10** each, in 124.366 and 151.640 seconds. It exercises the production
factory, readiness metadata, main Handler, client and remote Binder and proves
one bounded request plus Original on equal scores. These are functional
durations, not latency or energy measurements.

No real-model punctuation quality claim is made. Frozen contextual holdout,
automatic Binder qualification, physical Fold typing/lifecycle/performance and
energy, public immutable model release, remote CI and version 0.3.0 remain open.
No push, remote PR or publication was performed.

Evidence: `tools/qa/smart-typing-0.3/results/2026-09-03-contextual-punctuation/`.

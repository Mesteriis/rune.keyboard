# Original spelling regression snapshot

This profile runs the already-versioned `spelling-en.jsonl`, `spelling-ru.jsonl`,
`spelling-es.jsonl` and `protected-tokens.jsonl` from
`tools/eval/smart-typing-0.3/`. Their provenance and licensing scope remain in
that directory’s README and manifest. The separate FrequencyWords CI corpus’s
CC BY-SA declaration does not assign a new license to these authored sentences.

Only ID, split, language, prefix and typed token are projected for the observer;
IDs become opaque ordinals. Existing expected labels/candidate lists are not
sent to Kotlin or used to select a policy. The snapshot retains all 12,000 rows,
4,000 per language. It is disclosed historical regression data, not fresh holdout
or evidence that its authored labels are valid. Contexts, typed/candidate
surfaces and unproven RU surfaces are permanently registered with Q6; no new
canonical lemma claim is made.

The compressed baseline comes from the new canonical 12,000-row capture recorded
in `docs/acceptance/2026-10-28-q7-portable-replay.md`, not old evidence hashes that
used another projection. Exact current core/asset bytes were rechecked before
adopting it. The comparator excludes only the two declared host timing fields.
The CI job runs this historical profile and the separate licensed v1 profile.

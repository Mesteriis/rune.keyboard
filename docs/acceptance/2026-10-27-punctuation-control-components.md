# Q6: register historical punctuation components

Added all 3,600 punctuation rows from qualification-v2 and compact-v3/v4: 400
per language/component, covering RU, EN and ES. Exact pinned manifests/component
hashes, public/frozen flags, archived generator/source-lock bytes, source-selection
hashes, original split wrappers, boundary candidate index and noAuto flags are
verified. No row, label, old generator, lexical key or model is changed.

A separate control registry provides explicit language and control-kind
namespaces. Punctuation identity retains the exact NFC prefix/current word while
excluding the expected boundary, preventing relabeled old contexts from appearing
fresh. Command/name/identifier token preservation belongs to the separate
protected-control stage; neither control type is treated as a lexical lemma.

The lexical registry and its article overlap report remain unchanged. This step
persists punctuation context exposure, not recovered source articles. Source
article/window recovery remains pending. The complete preparation protocol still
needs both registries wired into versioned builders. Schema validation is not
fresh-data qualification, and unknown controls fail incomplete coverage.

Ten new control tests cover namespace separation, label-independent punctuation
identity, exact-case/punctuation preservation, NFC, invalid flags/IDs/schema,
false completeness, duplicate entries, incomplete freshness and durable snapshots.
All 82 existing/new tests pass in a source-only directory without original data,
models, PyArrow or morphology packages. CI includes both schema validators and
the unit tests; no remote CI execution is claimed. The accompanying receipt binds
original inputs, final registry and checks. No APK or Fold action.

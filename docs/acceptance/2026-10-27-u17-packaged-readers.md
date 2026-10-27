# U17 — packaged readers and bounded decoding (partial)

Android morphology, rare-word and contextual feature loaders now use
`openPackaged` for fixed paths mapped read-only directly from the APK, with exact
frozen sizes. Loading checks magic, counts, offset tables and bounded anchor
records. It does not hash every body or traverse every record. These APIs are
internal; imports/downloads cannot use them through the Android loaders.

Strict `validate` retains the single-digest body/trailer and full-file identity
checks. It walks every record, checking ordering, exact block ends, record counts
and payload values. Morphology and rare-word validation previously checked only
block anchors after hashing; their strict paths now reject resealed damage in
interior records too. Existing `open` APIs delegate to `validate` for compatibility.

Lookup checks prefix/suffix lengths, record boundaries and numeric payloads
before using them. Context lookup copies at most 1,024 payload bytes, validates
that bounded copy and only then exposes it to feature decoders. Invalid grammar
POS/number indices return no analysis instead of indexing beyond an array.
Malformed pair counts do not become numeric features. These checks do not
authenticate an otherwise valid corrupted word or number. APK trust and the
reduced bitrot detection are documented beside the trie fast-path rationale in
`docs/ARCHITECTURE.md`; tests explicitly show body/trailer corruption which the
fast path may accept and strict validation rejects.

Validation:

- Final full app JVM suite: 1,275 tests, zero failures/errors/skips. Fourteen
  added cases cover both lexical readers, context records/views, payloads and
  real grammar. The grammar test exercises all 128 POS/number bit combinations,
  including invalid indices and maximal valid remaining bitfields.
- Frozen morphology/rare membership and exact wiki/conversation counts/features
  agree between strict and packaged readers. The real frozen grammar agrees on
  all 49 Python golden feature vectors and exact strict/packaged vectors.
- `:app:lintDebug` and `tools/verify-scoring-boundaries.py` pass.
- Replay driver unit suite: 22 pass, one skipped. The skipped test requires
  `FINAL_REPLAY_EXPORT` for live-model delivery admission; this ordinary replay
  does not provide that export and does not claim native inference coverage.
- Three fresh source-bound 12,000-row product runs pass: parent commit strict
  readers, candidate strict readers, and candidate packaged readers. Every
  projected decision is identical. Only `hostStageNanos` and
  `fullTokenGenerationNanos` are excluded. Projection SHA-256:
  `33c3a96fed5b3322601f6b7a0307e3a4b62bfbc9bc7650b82bf644a1afffd8a3`.
  Candidate packaged mode uses the explicit JVM property
  `-Drune.replay.packagedAssets=true` in the developer-only Kotlin harness.
  It fully validates each asset first, then selects the packaged handle for
  actual decisions; ordinary replay still defaults to strict readers.
  Compile sources/assets are bound before and after each run. Both candidate
  runs use the same compiled harness source, and all runs use the current owner
  Python driver with each checkout's source manifest/harness. The adjacent JSON
  binds sources, assets, commands and results. This proves parity on the fixed
  ordinary corpus; it does not remove existing EN/ES quality limitations.
- All 13 pre-existing dirty tracked files retain their exact contents; all 98
  pre-existing untracked paths remain. No phone commands or installation occurred.

The first focused attempt failed while compiling a new test helper because a
returned lambda was parsed as a trailing call argument. The helper was corrected;
the subsequent focused and full runs above passed. That attempt's log/exit are
retained separately from the final evidence.

U17 remains open for disabled-RU loading and before/after profile/PSS/startup
measurements on Fold and a constrained API 26 device. No startup-speed or memory
improvement is asserted from these host checks.

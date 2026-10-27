# U17 — single body digest (partial)

The morphology, rare-word and context readers previously fed the same body to
two SHA-256 instances. They now share a bounded helper: hash the body, clone the
digest state, verify the body trailer, and append that trailer to the clone to
verify the frozen full-file identity. Providers without cloning support retain
both integrity checks through a bounded second pass using the reset digest.
Calls without an external identity still verify the body trailer. Interruption
remains a load refusal and is not cleared by production code.

This step preserves strict loading. Header, block, record and payload checks
remain in their existing readers; no packaged fast path or new trust boundary
has been introduced. The helper is included explicitly in the product replay
compilation manifest.

Validation:

- All 1,261 app JVM tests pass, zero failures, errors or skips.
- Five new digest tests use scoped real SHA-256 providers with counted updates.
  A cloning provider processes exactly the sealed file's byte count; a provider
  without cloning processes the body plus the complete sealed file. Tests cover
  body/trailer corruption even with a rebound full-file hash, resealing against
  an old frozen hash, cancellation and a nonzero input position.
- Two new real-asset tests verify the frozen sizes and identities of both
  `ru-wiki.ctx` and `ru-conversation.ctx`, exact independently decoded counts for
  three pairs in each table, six resulting feature values, absent pairs, wrong
  identity and body/header/trailer mutations. Existing parser mutation tests
  remain green. Counts were independently read from the frozen front-coded
  records using Python struct decoding before being put in the JVM assertions.
- A fresh baseline/candidate product replay produces identical decisions on all
  12,000 fixed rows. Only `hostStageNanos` and `fullTokenGenerationNanos` are
  excluded from comparison; projection SHA-256 is
  `33c3a96fed5b3322601f6b7a0307e3a4b62bfbc9bc7650b82bf644a1afffd8a3`.
  The baseline clean checkout's affected existing sources equal the parent
  commit's sources. Both compilations use the same current owner replay driver,
  each checkout's explicit source manifest, and checked-before/after source and
  asset identities. Exact bindings are in the adjacent evidence JSON. This is
  ordinary product parity, not native inference or renewed quality qualification;
  the existing EN/ES qualification limitations remain.

This receipt does not establish a startup-time or PSS improvement. U17 remains
open for packaged fast paths, safe decoding of accessed records, disabled-RU
loading, and profile/PSS/startup measurements on Fold and constrained API 26.

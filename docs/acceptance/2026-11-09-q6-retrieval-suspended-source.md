# Q6: resolve the disclosed retrieval suspended-hyphen boundary

The one `SOURCE_BOUNDARY_COMPOUND` row retained in the historical retrieval
boundary audit is `retrieval-0b33fc8fd3060a72f19480bf`. Its exact parent prefix
and target occur once in article 3089989 of the pinned Russian Wikipedia
shard. The source reads `аудио- и видеофайлов`: `аудио-` is a suspended
compound prefix, followed by the separate observed word `видеофайлов`. The
source does not supply a complete `аудио-…` token at that position, so none is
invented and no compound family is asserted. The original audit and its
unresolved record remain unchanged as historical evidence.

The source article snapshot, attribution and contributor-history link are
retained in `retrieval-suspended-source-v1`. Two added entries quarantine the
two observed source forms and contexts in the control and lexical ledgers;
`видеофайлов` also has an exact unsupported-surface exclusion without a
guessed lemma. This is a conservative disclosure of inspected source, not a
claim that the historical selector consumed that following word. The 62 prior
control entries and 213 prior lexical entries and all coverage declarations
are unchanged. Both registries remain incomplete.

The pinned shard's 170,922,988 bytes matched its SHA-256
`39b59952cd92a148b301f4d2b3ae1fb71e4caab987c6abe278f0dbdf0b01bb88`;
the retained NFC article bytes hash to
`ad02c5743093de5e1d2abc976d45471a0b69c594d96f481cd9d5dc9cc3d082e7`.
Two complete PyArrow 25.0.1 shard reads independently matched the retained
article and projected both source records. The source lock, article, parent
corpus, relevant helper bytes and registration code are bound. The first two
registry generations were byte-identical before the final helper/notice
binding additions; they are not claimed as a reproducibility check of those
later binding bytes. The archived helpers used by previous checks are intact.

Six focused tests pass, including changed article, duplicate or mismatched
source, ambiguous boundary, changed helper, and a candidate using
`видеофайлов` with a different article and context. Removing only these new
entries removes that exact surface overlap. All six tests and the registration
check also passed in a source archive without `build/`. The public lexical-ledger suite passed 24
tests after explicitly incorporating the new entry; the prior assertion of a
fixed old count failed before that adjustment. The previous retrieval-boundary
tests and check, 27 public-preparation tests, 11 text-preflight tests and the
isolated historical text-boundary checks passed. The local standard-library
inventory passed 183 modules and 905 tests with zero failures, errors, skips,
timeouts or missing receipts; inventory validation and its nine tests passed.
This full run used the working checkout; the targeted archive test above is
the separate no-`build/` evidence. Hosted CI, the scientific inventory and
device acceptance were not run for this change.

The temporary public shards, intermediate registry outputs, archive and
scripts were removed. This closes the source interpretation for one historic
row; it does not establish complete provenance, full family coverage or a
fresh independently qualified corpus.

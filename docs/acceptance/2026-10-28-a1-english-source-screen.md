# A1: English source screen, not qualification

The public Tatoeba English CC0 snapshot retained under
`tools/typing_experiments/public_sources/tatoeba-en-cc0-20261024/` contains
41,513 tab-separated rows; the compressed file passes `bzip2 -t`. A preliminary
literal Unicode-word-boundary scan finds 5,663 sentences containing standalone
uppercase `I`, four containing standalone lowercase `i`, one containing `i.e.`
(case insensitive), and none with `chapter i` (case insensitive). These are
sentence counts, not verified labels, distinct authors, a precision estimate or
a product replay. Possessive/contraction and non-ASCII boundaries need separate
handling; the scan is not an autocorrection policy.

The low control counts mean this source alone cannot qualify A1. Its prior
English exposure, sentence/template overlap, licensing/source identity and
registry coverage must be audited before any independent evaluation. This
screen disclosed the source and did not alter the keyboard or train a model.
The source is not evidence for code, Spanish or Roman-numeral controls.

The versioned `screen_english_i_source.py` now counts occurrences by the next
character, separating uppercase `I` before a space (5,096), an apostrophe
(1,560), the proposed non-period punctuation boundaries (13), a period (9) and
other characters (1). Lowercase `i` occurs four times: one before a space, two
before periods and one before other proposed punctuation. These are raw
occurrences, not verified pronouns or correctness labels; the script does not
assign author, article or qualification splits. It verifies source digest,
language, row shape and unique IDs. Two fresh outputs were byte-identical with
SHA-256 `df6248e8e0611d8b29d8e298c167af08751362ccdf1dc35a465936658dc43e57`.
Three screening tests, including exact pinned-source counts, and seven CI
inventory tests passed. The screening test is in the versioned CI inventory;
hosted CI was not run.

The source also contains three lowercase occurrences immediately after an
apostrophe in `Baha'i`; two end at a proposed automatic boundary (one space,
one comma), while the third ends at a period. A token-only `i → I` rule can
therefore corrupt correctly spelled text unless it considers the left context.
These are disclosed source examples, not an independent false-change rate.
Five uppercase `I` occurrences also follow an apostrophe at an admitted
boundary, so blanket exclusion of those positions has a recall tradeoff and
needs separate labeling. The extended screen records these subsets and its two
outputs match SHA-256
`58349795589223b11e60095f19bb59e85e7cea6634a8c29f05a84eba8fad54c3`.
Four focused tests pass. The actual product currently has no A1 rule; this
screen tests a risk of the proposed rule, not a current product regression.

An agent-reviewed, source-bound review of the complete eight-occurrence subset
is retained in `english_i_apostrophe_review.json`. All five uppercase examples
are pronouns following an opening single quote at the start of text or after
whitespace; the three lowercase examples are the internal apostrophe in
`Baha'i`. The auditor verifies the source digest, exact occurrence coverage,
offsets and visible contextual constraints, and refuses missing, duplicate,
mislabelled and altered-source fixtures. The contextual checks are not a proof
that all future quote or apostrophe usage follows the same pattern. These eight
disclosed examples are development evidence, not a representative sample or an
independent qualification set. No product behavior changed.

The full snapshot is now registered as a disclosed historical-source exclusion:
41,513 distinct English Tatoeba IDs and 41,510 normalized sentence hashes. Three
duplicate normalized texts retain separate IDs. All 140 previous ledger entries
and the incomplete coverage declaration are unchanged. An actual source row is
refused on both article and sentence axes; fixture tests cover malformed and
duplicate IDs and changed source bytes. The shared identity namespace accepts
English explicitly while preserving existing Russian keys. This does not prove
author/template independence or complete historical coverage. A future English
collector must invoke the shared overlap guard.

The final stdlib inventory passed 725 tests across 135 modules with zero skips;
the focused ledger/identity/import suite passed 41 tests, and the CI inventory
check passed seven tests. Raw stdlib results are under
`build/review-a1-en-ledger-final-20261028/`. Hosted CI was not run.

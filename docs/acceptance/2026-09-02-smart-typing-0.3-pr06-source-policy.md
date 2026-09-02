# Smart Typing 0.3 — lexicon sources and policy checkpoint, 2026-09-02

Baseline: `b5400cbadadd29e8ee915a0fb33fb11ec5bebc79`.
Slice parent: `6c6b4dd43e8cbeb3f22ba44fb20a78ef8b7ae8cb`.
This checkpoint implements the offline source pipeline and pure orthographic
policies. PR6 as a whole remains incomplete: runtime format selection, bounded
candidate generation, asset packaging and end-to-end deterministic quality are
separate pending work. No model, keyboard binding, settings or version changes.

## Source contract and reproduction

The checked-in `tools/lexicon/smart-typing-0.3` package contains the immutable
source lock, frozen output manifest, original notices, transformations, native
host checker and command-line regression suite. The lock pins LibreOffice,
SCOWL, FrequencyWords and Hunspell revisions from the implementation plan.
Inputs are verified by exact SHA-256 and size; network acquisition is explicit.
Mutable sources/builds/results live in an explicit dedicated project build path.

Two fresh serial SCOWL builds and two finite RU/ES expansions completed offline
from explicitly supplied verified source archives. The native Hunspell checker
accepted each retained RU/ES finite form; EN uses the verified SCOWL selection. Final identities:

| Language | Canonical forms | UTF-8 bytes | SHA-256 |
| --- | ---: | ---: | --- |
| RU | 1,436,553 | 33,008,833 | `b54c01203aad985845c7b79116e57b818fde5e647f66f735bddb0b3239249401` |
| EN | 121,255 | 1,173,857 | `67f5299ebd264abb62518b01dae9ea36837d39dfcfe76d731983841bc9794d26` |
| ES | 668,267 | 7,791,505 | `0a304ca9c3269498f82e573b44c9b80f4135e6e596ed947205cfa26b6f4530dd` |

All 38 promoted package files are byte-identical to the reviewed, fully reproduced
overlay. Running the root package verifier against that output then passed all
24 frozen output/notice/lock identities and current tool provenance. The failed
legacy `unmunch` comparison is an expected diagnostic demonstrating why that
utility cannot replace the finite expander. Finite-profile coverage limitations
and four rejected ES forms remain explicit in the package README; these outputs
are not claimed to enumerate arbitrary Hunspell compounds.

RU retains its original permissive notice, ES its separate MPL component, EN the
complete multi-source SCOWL notices, and frequencies separate CC-BY-SA data.
Hunspell is host-only. Original notice whitespace is preserved with the exact
hashed source bytes; source whitespace checks exclude only those notice files.
No dictionaries/frequencies/Hunspell are packaged into the application yet.

## Pure policies

Protected-token classification covers technical shapes, mixed scripts, unusual
characters, long tokens, mixed case and multi-letter ALLCAPS. Routing uses script
and Spanish markers first, then a 4:1 active EN/ES prior and an explicit maximum
of two fallback candidates. The future generator must enforce that limit.
NFC/ROOT casing preserves accents, ñ and ё and rejects malformed or oversized
input rather than truncating. Static keyboard adjacency is a feature, not device
geometry. Case preservation rejects unsupported mixed/uncased transformations.

Weighted unrestricted Damerau–Levenshtein uses bounded reusable scratch and
integer quarter-costs. Initial insert/delete/substitution costs are 1, adjacent
substitution 0.75, transposition 1.25. Repetition is a separate feature. These
are initial features, not calibrated AutoReplace thresholds. Independent graph
edit-path tests cover 6,400 pairs plus the unrestricted `CA -> ABC = 2` case;
they do not constitute a proof over every Unicode string.

## Actual checks and remaining gates

- Root offline source regressions: PASS 23/23, no source fetch or native build.
- Root verification of fully reproduced outputs: PASS 24 identities.
- Fresh integrated JVM: PASS 332/332, zero failures/errors/skips.
- Full requested lint/build/privacy/dependency/native gates: PASS, 238 tasks,
  48 executed. Source tests are added to ordinary CI, which has not run remotely.
- API26 three-format benchmark smoke: all nine processes PASS; complete-reference
  timing/format selection and cold-process measurements remain pending. A first
  full run overlapping host builds is explicitly diagnostic, before viewing its
  times; only an unchanged quiet-host run may drive the selection.
- New policy execution in the real Android candidate pipeline: NOT IMPLEMENTED.
- Deterministic and final assisted holdout quality: NOT QUALIFIED. Frozen PR1
  prepared-candidate Rune Text suitability remains FAIL without retuning.
- Physical Fold, battery/latency, new remote CI and model publication: BLOCKED
  by their separate device/authorization/qualification prerequisites.

Independent source promotion review identified writable-leaf symlink escape and
unverified frozen-manifest identity. Both were fixed and independently approved.
The boundary covers a pre-existing single-writer build tree, not arbitrary
concurrent filesystem substitution. Independent policy review approved the exact
proposal without P1/P2 findings.

Local evidence: `build/smart-typing-0.3/pr06-source-regressions.log`,
`pr06-promoted-source-verify.log`, `pr06-policy-jvm-integrated.log`,
`pr06-source-policy-gates.log`, and `lexicon-pipeline-promotion/reports/full-reproduce.log`.
No push, remote PR, publication or version bump is part of this checkpoint.

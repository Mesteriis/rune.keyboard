# A1: English Web Treebank source screen

The public [Universal Dependencies English EWT repository](https://github.com/UniversalDependencies/UD_English-EWT/tree/b7711cce01cdd4f5fcc0a8199b8a50d951b16c0c)
at release `r2.18`, commit `b7711cce01cdd4f5fcc0a8199b8a50d951b16c0c`,
declares CC BY-SA 4.0 and identifies the underlying English Web Treebank and
contributors. Its cited work is Silveira et al., *A Gold Standard Dependency
Corpus for English* (LREC 2014). The source includes weblogs, social text,
reviews, email and web text; annotations have mixed manual and automatic
provenance. The downloaded files remain in ignored `build/` and are not bundled
with Rune. Do not treat their personal-looking source material as user data.

Only the training partition was screened for development. The aggregate-only
script pins its SHA-256 `d68e06122a702464c613076523d56740f047e5bbe89dd90ec32737e04d952143`
and emits no sentence text or source IDs. It counted 12,544 sentences in 540
documents, 255 annotated lowercase `i` PRON tokens, two lowercase `i` NUM
tokens and 3,122 uppercase `I` PRON tokens. Raw text-boundary counts include
221 lowercase `i` before whitespace and ten before a period. Text and token
counts use different tokenization and cannot be added or treated as correctness
labels. Annotations, meaning and exact context still require independent review.

At the initial screen the dev and test files were downloaded and hashed but not
screened or scored. They were subsequently read for the exclusion import below;
they have not been evaluated as a holdout.
Their SHA-256 values are respectively
`39239e0a60db3ae68f4b7036189f11b6692741d10ff8240dd91f74f2760d90f8` and
`fa024f43dc5da3c5ac02563bc9bd0e974f46cbb1560823976a8f342a37dc494a`.
The complete source is considered exposed for independence purposes. This screen
is not natural-holdout qualification, a precision estimate, or evidence that
the proposed rule is safe.

`screen_english_ewt.py` SHA-256 is
`131dffca054550e26fb111f94303832c9082710ad0afc3c87547f725b67cac95`;
the aggregate output is `build/review-a1-ewt-screen-20261028/aggregate.json`
(SHA-256 `ed44101b608104f97c595b6dd6c3ba2ffa1a93087453f2d33aba01d5dffddc40`).
Two focused parser tests passed; they cover malformed or duplicate IDs and check
that the aggregate output contains no source sentence. No product behavior was
changed.

## Full-source exclusion import

All three pinned files were subsequently parsed for document identities and
normalized full-sentence hashes. The shared holdout ledger now excludes 16,622
rows, 1,174 distinct document keys and 15,483 distinct normalized sentence keys;
the original 141 ledger entries and incomplete-coverage declaration are
preserved. EWT document identities use a separate namespace. Normalized sentence
keys deliberately use the pre-existing Tatoeba full-sentence namespace, despite
its historical name, so the same text cannot evade exclusion by changing source.
The importer found zero matches against pre-existing keys in that compatible
namespace. This does not compare against all legacy namespaces or prove author,
template or broader corpus independence.

The shared holdout guard rejects both an EWT document and a repeated normalized
sentence, including when that sentence is presented as Tatoeba. The separate
control registry does not yet support EWT document IDs and rejects them rather
than silently treating them as fresh. The source lock is
`tools/typing_experiments/public_sources/ud-ewt-2.18/source-lock.json`; source
files remain local ignored build artifacts and can be retrieved at the pinned
commit. The ledger SHA-256 at this checkpoint is
`5c15acbb41f09ef01e344302c35261953af579a53b10ab17bfeb416bca8e6175`.
Tests cover source hashes, all three partitions, cross-source overlap, malformed
document identity, duplicate import and the separate registry's refusal. No
fresh qualification or unexposed EWT split is claimed.
The full stdlib inventory passed 741 tests across 140 modules with zero skips;
raw results are in `build/review-a1-ewt-ledger-tests-20261028/`.

## Development context and current behavior

The current-product controller was replayed twice on the disclosed contexts
`yes i`, `chapter i`, `si i` under Spanish, and `yes ii`. All were retained;
`yes i` offered only the original, not `I`. The four exact contexts are now
recorded in `control-ledger.json` and
`tools/typing_experiments/a1_controls/initial-replay-v1.jsonl`. The raw replay
receipt is `build/review-a1-initial-replay-20261028/receipt.json`, SHA-256
`919eb9917025edb9b00019469bcb3a57378f6bdb822fed502579071f70acbf11`.

An aggregate context audit of EWT training aligns exact raw I/i occurrences to
their annotated token sequence only when the entire sentence's occurrence list
matches. It reports 2,573 aligned sentences and excludes 29 sentences containing
39 unaligned occurrences; tokenization disagreements are not guessed. Among
aligned tokens, 209 lowercase pronouns precede whitespace (144 preceded by a
word and 65 with other or no left context), and 19 lowercase pronouns precede an
apostrophe. The only two lowercase non-pronouns are followed by other characters,
outside the proposed punctuation/space subset. Thus the observed zero opposing
previous-word collisions in that subset is vacuous: this training sample does
not validate the Roman-numeral, code, Spanish or abbreviation controls. POS tags
and synthetic lowercasing are not verified typing intent.

The context auditor returns counts only and no raw text or source IDs; it binds
the pinned training file. Its source SHA-256 is
`02e52758c7e666f235fdffb211e4e9474fd04d797cb162c1e5a821eef6189a1f`, and
`build/review-a1-ewt-screen-20261028/context-aggregate-final.json` is
`7080fa80f2c455b655d62b054e229a775c46fa08703770f178bf31f15889a83a`.
An earlier exploratory output misclassified an empty next character as
punctuation due to Python substring semantics; that code was fixed and a
sentence-end test added. No product rule was enabled or independently qualified.

Follow-up: the control-registry limitation described at this historical
checkpoint was addressed by the [EWT control source registration](2026-11-03-q6-ewt-control-source.md).
English family qualification and global coverage remain open.

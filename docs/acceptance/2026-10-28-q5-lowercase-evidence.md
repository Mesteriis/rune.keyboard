# Q5 lowercase evidence for canonical-case ambiguity: exploratory screen

A source-bound screen compared all 16,293 Russian canonical-case keys currently
marked unambiguous with non-sentence-initial words in the retained Tatoeba CC0
snapshot. Only articles already excluded by the permanent ledger were used.
Ten keys had at least one distinct article with a lowercase occurrence; two of
them also had title-case occurrences. Examples include the reviewed `клавы`,
`читы`, `моника`, but also `ника`, `господи` and `марсе`. A lowercase surface
is evidence of a possible common use, not proof that every occurrence of the
same spelling is a common word or that a user wants lowercase.

On the already disclosed and post-hoc 30-case review, all five lowercase
preservation cases had such lowercase source evidence, and all 24 cases labeled
as apparent proper names had no lowercase evidence and at least one title-case
source occurrence. The one ambiguous case had lowercase evidence. These groups
are small and the same source and cases were used to select this idea. The
result does **not** measure the effect of changing Rune, establish word intent,
prove these ten surfaces are unambiguous, or provide an independent holdout.
For example, `ника` may refer to a person or a nickname. A production rule
requires additional provenance, context-aware controls and actual replay;
a blanket suppression would risk losing legitimate name capitalization.

The [screen](../../tools/typing_experiments/screen_case_lowercase_evidence.py)
checks the frozen RNC1 asset identity and structure, source hash, unique public
article identities, ledger exclusions and reviewed labels. It counts distinct
articles, not raw duplicate token frequency; mixed-script and numeric attached
words and initial words are excluded. The [receipt](2026-10-28-q5-lowercase-evidence-screen.json)
binds inputs and tools. Two final runs matched byte for byte. Three tests cover
asset corruption/order, sentence position, source exclusions and malformed review
entries. The first test run had a fixture argument error, corrected before the
final runs. No runtime policy, APK or phone was changed.

# Q6: preserve source-verified public conversational history

Imported five pinned public corpus groups: context-feature conversation,
supervised-v2, promoted follow-on, supervised95 and grammar-context evaluation.
Together they contain 97,347 labeled rows across ten partitions. Every frozen
manifest/row hash and original count is checked. No model scores/results are
read. The original rows, flags, labels and contributor/source attribution stay
in their original local files and are not redistributed as corpus text here.

Verified the original compressed CC0 and CC-BY-2.0-FR Russian Tatoeba exports.
All 23,077 preprocessed CC0 sentence IDs and 16,000 selected detailed-source IDs
match their actual normalized full-sentence hashes. Every imported prefix is
also captured in the actual source sentence, avoiding reliance on IDs alone.
Source-only CC0 splits exclude complete sentences; they do not pretend to be
labeled target-family corpora. The three explicit source-only entries have a
strict article + full-sentence scope. Four-axis target corpora remain separate.

Source IDs now use an explicit Tatoeba namespace: sourceRepository=tatoeba,
language=ru and article=tatoeba:<ID>. Full sentenceHash keys have a distinct
namespace from right-context window hashes. Wikipedia and Tatoeba numeric IDs
cannot alias, bare Tatoeba strings still fail, and every existing Wikipedia
identity remains compatible. Both registries and new preparation entry points
understand the typed identity. Source-backed protected rows also receive lexical
source-ID/full-text checks instead of bypassing them as authored controls.

Native numeric family IDs are not canonized. Every supported target analysis
comes from the pinned dictionary; protected @word forms are classified using
original group=protected, noAuto and unchanged-target construction, including
old cohort=correct rows. The first extraction diagnostic counted 22,463 mentions
as unsupported; the corrected group-aware classification and new regression
leave **zero unsupported lexical targets in these five groups**. No prediction
or stripped arbitrary token is used as a lemma.

The supervised-v2 train target families are supervised exclusions. The old
follow-on holdout's later training promotion is verified against the supervised95
plan's exact promoted path/row hash; its 2,094 dictionary family keys are therefore
supervised exclusions too. Evaluation partitions remain historical exclusions.
This records past exposure; it does not train on a holdout now.

All prior entries/keys/source bindings and incomplete global coverage are
preserved. No private/user-authored regression corpus is silently imported.
Other derived context/evaluation histories and original source/runtime bindings
still need inventory; this is not completion of all conversation history.

All 121 tests pass in a source-only directory without original corpora, models,
PyArrow or morphology packages. Eleven new tests cover source namespaces,
full-text/window separation, source-only scope, public source IDs/hash/prefixes,
protected mentions, numeric-family separation, promotion, source-backed protected
preparation and persisted snapshots. CI includes these suites; no remote CI run
is claimed. Extraction itself uses the pinned dictionary and compressed sources.

The accompanying receipt binds inputs, dictionary code/data, final ledger and
successful checks. Both registries still deny fresh final publication; no new
qualified corpus, model, threshold, APK or Fold action is produced.

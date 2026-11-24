# Q6: classify and quarantine unsupported lexical targets

## Additional exact forms from UniMorph

The public [UniMorph Russian data](https://github.com/unimorph/rus/tree/50dcabfd0a04bd4d187ffb0d5cdd54af94863dec)
declares Wikipedia as its source and CC BY-SA 3.0. Two independent downloads
matched Git blob `84860e20a2bdcca277286ed937baadeb5b40e69e`, 25,151,401
bytes and SHA-256 `6c13f849fc12844b23f46e70a02a45a2f537e60c62c8ffd8798bdff3991dc880`.
Exact NFC/casefold matching against the hash-verified early RU qualification-v2
parent found two of its 171 dictionary-unsupported target surfaces. UniMorph
lists 14 distinct lemma/form pairs for the two matched lemmas. All 14 exact
form keys are now excluded; 11 were new. The new entry also binds the two
already-disclosed historical contexts and preserves the existing entries and
incomplete-coverage state.

The initial source-derived fixture contained those 14 public lemma/form pairs;
the expanded fixture below supersedes it. The source's stated morphological
relationships do not prove the intended sense of either historical example;
they are used conservatively to reject exact forms. They are not inserted into
the Pymorph lemma namespace. Other possible forms, canonical family coverage and
independent qualification remain unproven.

The normal `--check` verifies the current tracked fixture, original parent,
helper bindings and ledger entry without downloading the 25 MB source. The

All 219 previous entries and the incomplete-coverage declaration were compared
against the preceding commit and preserved. The new entry's real preparation
preflight rejects a form that the preceding ledger did not exclude. The
stdlib inventory passed 928 tests in 187 modules without failures or skips
before a subsequent portability fix. An initial no-`build/` check then failed
on macOS `/var` versus `/private/var`; after resolving the paths and updating the
new entry's source binding, all four focused tests, including an isolated
no-`build/` check, passed. The earlier snapshot test initially failed because
it assumed a fixed count; it now verifies the new entry separately while
retaining the original 13-entry assertions. The full inventory was not rerun
after the portability fix. No runtime, APK, model or phone was changed.

## Expanded historical exact-form coverage

The same pinned source was matched against unsupported surface keys from all
11 original spelling, ranker and early-RU parents. These parents retain 1,357
distinct target keys; original build files are not needed for the key match.
There are 15 distinct exact matches to source forms, associated with 11
UniMorph lemmas. The expanded source fixture retains 100 distinct lemma/form
pairs, including all original 14. Of the corresponding exact surface keys,
73 were absent from the preceding complete ledger. The previous two historical
contexts remain the context anchor; they do not claim context coverage for the
other parents. The entry binds the full canonical digest of every parent.

Two independent pinned-source downloads produced the identical expanded
fixture. `import_unimorph_early_exclusions.py --capture <pinned-rus> --check`
reproduces it; the ordinary `--check` works without the source or `build/`.
This is conservative exact-form quarantine, not proof of historical intended
lemmas, coverage of inflections absent from UniMorph, or complete Q6 coverage.
All 219 other entries and the incomplete-coverage declaration were unchanged;
the previous 14 form keys remain. A real preparation preflight moved from zero
to one unsupported-surface overlap for a newly excluded form. Four focused
tests, including source/parent mutation and the no-`build/` copy, passed, as
did the adjusted historical snapshot and test-inventory check. The first focused
run failed because the test expanded packed parent entries before comparing
their raw bindings; the corrected test preserves the serialized form. A full
inventory was not rerun for this extension. Temporary source downloads and
the isolated copy were removed; no runtime or device change was made.

## Neighbor-prefix interior words

The previously disclosed 15,000 neighbor rows also contain 1,163 unsupported
prefix surface keys. A broader screen produced matches that could be truncated
fragments; those were not used. The importer now only accepts a Cyrillic word
strictly inside a retained prefix with whitespace on both sides, checks the
three retained row files against the existing parent bindings, and intersects
those words with the parent's unsupported keys. The 590 distinct qualifying
unknown surfaces include three exact UniMorph matches. Their three UniMorph
lemmas have 26 listed forms, of which 23 keys were new to the preceding ledger.
The expanded fixture now has 126 pairs from 14 source lemmas and retains all
previous 100 pairs. Two independent source captures matched byte for byte.

The existing entry now also binds the neighbor parent digest and its three row
files. Its two context keys still describe only the early-v2 anchor, not every
neighbor context. All 219 other entries, previous exact keys and incomplete
coverage were preserved. A real preflight blocked a newly added form that did
not match the earlier exact-surface registry. Five focused tests, including
prefix boundary/compound controls, source/parent mutation and a temporary
no-`build/` tree, passed; the relevant public-ledger snapshot and test inventory
also passed. The full stdlib profile was not rerun for this extension. The
source downloads and temporary tree were removed. No lemma namespace, product
policy, model or APK changed; Q6 remains incomplete.

## Source-bound historical text screen

A diagnostic screened all 1,699 retained refinement, word-ranking and
additional-epoch text records against 1,699 corresponding articles from the
already pinned Russian Wikipedia shard. The shard's 170,922,988 bytes matched
SHA-256 `39b59952cd92a148b301f4d2b3ae1fb71e4caab987c6abe278f0dbdf0b01bb88`;
the two archived corpora were verified by their existing fixture verifiers.
For each cleaned fragment, the screen checked the exact article prefix and
word-ordinal mapping, excluded words truncated at the fragment end, and used
the existing `source_fragment` guard to reject words joined to other source
characters. All article mappings were present and no Unicode case-mapping
refusals were reported.

Among 11,799 distinct standalone unknown surface keys in the existing parent
entries, the pinned UniMorph source matched 59. Its 52 corresponding source
lemmas list 528 exact forms; 460 of those form keys were absent from the
current ledger. These are candidate exclusions, not a completed import or
canonical-family proof. The screen retained no per-match source evidence, so
it is insufficient to modify the permanent registry. A reproducible,
source-bound projection and mutation checks are still needed before import.
The first attempt failed at token mapping because it checked a truncated final
word before applying the truncation guard; the reordered diagnostic completed.
Both temporary 171 MB source downloads and isolated PyArrow environments were
removed. The decoder version was pinned to 25.0.1 but its installed wheel was
not independently hash-attested. No model, product, registry or device changed.

## Source-bound text-form import

The candidate screen above is now backed by a retained source projection:
63 parent/article/word-ordinal records cover 59 distinct previously unknown
surfaces across seven historical text parents. Two complete runs of the final
auditor matched the projection bytes (SHA-256
`87b639162951bc50c835728b70e8054ae98566b847041f7dd050e5484ffd006f`), with
both public sources hash-checked and the archived inputs rechecked after each
run. PyArrow 25.0.1 was required, but the installed decoder wheel was not
independently hash-attested. The portable verifier binds the projection and
auditor, checks its records against the hash-bound archived fragments and
parents, and needs neither the original Parquet file nor `build/`. It cannot
independently re-establish the source-side boundaries without rerunning the
auditor on the pinned source.

The UniMorph fixture now contains 644 exact forms, including all previously
protected forms; 460 keys were absent from the immediately preceding ledger.
All 219 other entries and the incomplete-coverage declaration are unchanged.
The real preparation preflight rejects a new form that had no earlier exact
surface overlap. Five importer tests, two boundary tests, all 25 public-ledger
snapshot tests, all 27 preparation-gate tests and the stdlib test inventory
check passed. The full stdlib suite was not rerun for this change. Temporary public downloads and the decoder
environment were removed. No Pymorph lemma was inferred and no runtime, model,
APK, device or independent qualification changed.

## Russian Wiktionary exact-form exclusions

The [ruMorph Wiktionary snapshot](https://huggingface.co/datasets/SergeyShk/rumorph-wiktionary/tree/768e78b0f415f51c60d73c15362218452e30dbcc)
is derived from [Russian Wiktionary](https://ru.wiktionary.org/) and declares
CC BY-SA 4.0. Its compressed 24,457,732-byte file matched SHA-256
`0ff28409baca56faf67d83fdfc47e967dd6e61b30e5d9afc32c65af80a5a62c5`.
Two independent downloads and extractions reproduced the same fixture: among
250,917 source entries, 559 already-disclosed surface keys matched; the
selected 519 normalized headwords provide 4,235 headword/form pairs and 4,131
distinct exact forms. The fixture retains 536 exact source page titles (with
their original case), enabling attribution to Wiktionary contributors through
each page's revision history. Source data and this derived fixture are subject
to CC BY-SA 4.0; source title history links can be formed as
`https://ru.wiktionary.org/wiki/<URL-encoded-title>?action=history`.

All matched dictionary entries contribute forms, including ambiguous
alternatives; combining accent marks used for stress are removed, while ё is
preserved. These relations conservatively block exact strings; they do not
establish an example's intended sense or add guessed Pymorph lemmas. Of the
4,131 keys, 3,016 were absent from the prior ledger. The entry binds the prior
source-verified UniMorph entry and its 19 historical parents; its two context
keys remain the earlier v2 anchor, not a claim of full context coverage.
The pinned dump can reproduce the fixture via
`import_wiktionary_historical_exclusions.py --capture <dump.xz> --check`;
normal CI checks do not require the dump or `build/`. This does not complete
family coverage or qualify a corpus. The expanded fixture below supersedes
the initial 4,131-form fixture while retaining all of its pairs and titles.

All 220 previous ledger entries and incomplete-coverage metadata were preserved.
The real preparation gate blocks a newly excluded surface. Four focused tests,
including ambiguity, ё/stress normalization, fixture/parent drift and a
source-free no-`build/` check, passed; all 25 public snapshot and 27 preparation
tests and the test-inventory check also passed. An initial focused test failed
because its expected pair ordering was incorrect; the corrected test passed.
The full stdlib inventory was not rerun. Both downloaded source copies were
held in memory and no dump, temporary environment, model, APK or device change
was retained.

## Wiktionary expansion over source-bound historical text

The seven historical text parents were screened against the same pinned
Wikipedia shard using the existing source-bound word and truncation checks.
The new projection retains 1,957 parent/article/ordinal records covering
1,778 distinct exact source surfaces. It records no full article text. Two
complete runs of the final auditor reproduced both the projection and the
Wiktionary fixture; projection SHA-256 is
`cb464a1d545cecc8009b85500992f95448527655eda0097bd23e0a182510dd50`.
The auditor rechecks both source files, historical archives, helper bytes and
ledger stability. PyArrow 25.0.1 was required, but its installed wheel was not
independently hash-attested. The portable check verifies the pinned projection
against the retained fragment archives and parent keys without `build/`; it
does not independently reconstruct original source boundaries without the
pinned Parquet input.

The expanded attributed fixture preserves every earlier pair and title and now
contains 16,077 headword/form pairs, 1,774 normalized headwords, 1,815 original
Wiktionary page titles and 15,833 distinct exact forms. There are 10,118 form
keys absent from the immediately preceding ledger. All 220 other entries and
incomplete-coverage metadata remain unchanged. The preparation gate rejects a
new form that had no prior exact-surface overlap. Four importer tests, one
projection test, 25 public-ledger snapshot tests, 27 preparation-gate tests
and the test-inventory check passed, including a no-`build/` portable check.
The full stdlib suite and hosted CI were not rerun. Temporary source downloads
and the decoder environment were deleted. The result is conservative exact-form
quarantine; it does not prove intended senses or complete family coverage, and
does not change the keyboard, APK, model or qualification threshold.

## Additional public historical surfaces

The same pinned Wiktionary source was screened against 28 additional or
previously included public ledger parents with exact unsupported surface keys,
including Taiga, Q7 replay, truncated and retrieval disclosures. The selection
preserves all ambiguous Wiktionary alternatives and exact ё distinctions. The
source's 24,457,732 bytes matched SHA-256
`0ff28409baca56faf67d83fdfc47e967dd6e61b30e5d9afc32c65af80a5a62c5`;
a separate source download reproduced the same retained fixture. No source
download was stored. Source attribution and CC BY-SA 4.0 apply as described
above; the fixture retains original page titles for contributor-history links.

The 28 parents contain 11,091 distinct matched target keys; the source-bound
fixture contains 83,763 headword/form pairs and 79,503 exact form keys.
Of those, 54,808 keys were not in any of the 221 preceding entries. Only these
new exact keys are added in a separate entry; the other 221 entries and
coverage metadata remain identical. The fixture SHA-256 is
`21b99606e41c564f325cf534753ff5e35b9e6c8613749219b7f26ef9cdd78a6a`.
The versioned importer binds all preceding entry identities and its fixed
parent list. It can recheck the fixture without source downloads or `build/`,
and reproduce the source capture with `--capture <dump.xz> --check`.

These are conservative exact-surface exclusions, not inferred Pymorph lemmas,
intent or complete family coverage. A real new-family preflight rejects a newly
added form. The ledger remains explicitly incomplete; no fresh independent
corpus, model, APK or device acceptance is claimed.
The new importer tests passed twice; the earlier importer passed all four
tests. After updating the ledger snapshot for the added entry, all 25 snapshot
tests and 27 preparation tests passed. Inventory validation and the F-Droid
data policy passed, as did the staged source-only no-`build/` check. The
initial snapshot run failed solely on the previous exact entry count; it was
updated to assert the new entry and then passed. The full stdlib inventory and
hosted CI were not rerun for this change. Temporary archives were removed.

At clean source `88bd8d7becb7a64a019994d5d7b0259b8382cfba`, a temporary clone
with the pinned llama.cpp submodule and no initial `build/` ran the full
Python 3.12.14 stdlib inventory: 191 modules, 939 tests, zero failures, errors,
skips, expected failures, unexpected successes, timeouts or missing receipts.
The runner exited zero; receipt SHA-256 was
`179971f2b8be2cd68df1a7b8d5146739477e08c93f7b5f6d40a0f07c4b7740ea`.
The checkout was clean after the run, and its outputs and temporary copy were
removed. The isolated historical boundary runner also passed six original
tests and its registration checks against the expanded live ledger. This is
local evidence; hosted CI and independent qualification remain open.

Audited every remaining unsupported target in the registered historical spelling,
ranker and joint lexical inputs, plus the three early RU components. All original
row-file hashes/counts are checked. There are 1,402 unsupported row targets in
11 parent entries, representing 1,357 distinct NFC/casefolded RU word surfaces.
Every one invokes predictive analysis units in the pinned default analyzer.

Dictionary-only analyses remain the only canonical-family authority. The default
analyzer is used diagnostically to record method classes (known/unknown prefix,
suffix or unknown-word handling), not its guessed normal forms. A contradictory
all-dictionary result aborts for investigation. Predicted lemmas and probabilities
are never stored as family evidence or imported into training/exclusion families.

Each affected parent gains unsupportedSurfaceKeys. All its prior keys, bindings,
missing axes and global incomplete coverage remain unchanged. These exact-form
keys provide direct target reuse protection across source contexts, preserving
e/yo distinctions while normalizing NFC and case. They do not establish an
inflectional family or cover every other form of a name. The 1,402 canonical
family questions are explicitly unsupported, not silently marked recovered.

Protected mentions are checked against their original group/cohort/noAuto and
@word construction before being excluded from lexical analysis. Private/user
corpora are not imported. The receipt stores public row IDs, method names and
surface hashes, without source phrases, plaintext targets or guessed lemmas.
Hashes themselves are not claimed to anonymize private data.

New versioned preparation now checks both typed and expected unsupported
surfaces. A proposal using `ДАРСИ`/`дарси` cannot evade the exclusion by claiming
an unseen canonical family. This protection is independent of known context,
article, family and control matches; it changes no runtime correction policy.

All 129 tests pass in a source-only directory without build data, models, PyArrow
or morphology packages. Eight new tests cover diagnostic-only predictions,
protected construction, contradictory dictionary evidence, explicit no-analysis,
NFC/case/e-yo scope, malformed hashes, registry persistence and shared/CLI target
blocking. Current registries still forbid final corpus publication. CI includes
the tests; no remote CI run is claimed. Extraction uses the pinned dictionary.

Q6 remains open for complete derived-history inventory, unproven canonical
families/inflections and remaining historical source/runtime provenance. These
facts cannot be closed by substituting a predictor's plausible lemma. No model
fit, APK build or Fold action is performed.

# Q6: EWT lemmas already present in the packaged English dictionary

The historical public English EWT corpus was checked against the exact English
trie packaged with Rune. In addition to the 10,485 exact lemma keys previously
protected through the FrequencyWords vocabulary, 850 distinct EWT lemma keys
are present in that public trie and were not already in the prior lemma entry.
They occur in 1,469 integer-token rows. The new historical-family exclusion
protects those keys; all 207 previous lexical entries and the incomplete
coverage declaration are unchanged.

The filter uses the pinned public EWT source files and the source-attributed
SCOWL/FrequencyWords packaged dictionary; it adds only exact existing public
dictionary terms. It stores 850 unsalted hashes, not source sentences or
identifiers. The hashes are reversible by enumerating the public dictionary
and are not anonymization. There remain 3,118 recognized-shape EWT token rows
outside the union of the previously admitted frequency vocabulary and the new
trie matches, as well as 37,956 unsupported-shape rows. These counts do not
establish missing distinct families. No inflections or new lemmas are inferred;
English family coverage and independent qualification remain incomplete.

Both independent source extractions produced identical fixture bytes, SHA-256
`7a80f480bcd0f4162490086a851587d3ff83ce48a9830e69ed041bc59ec61a9e`.
Both registry generations were byte-identical. Source lock, previous EWT
projection, packaged trie, asset manifest and checker versions are bound.
The static checker revalidates those bindings without the original EWT files;
it does not re-extract the corpus. A synthetic new document with the public
lemma `gastroenteritis` has no matching family in the previous ledger and is
rejected by the existing new-families preflight after registration. This does
not qualify that document, label or any model.

The pinned EWT files were fetched into temporary storage for extraction and
removed afterwards. The packaged trie and notices remain tracked. The
language-specific reproduction and registry checks are wired into CI; no
hosted CI execution is claimed. No APK, model, or runtime policy was changed.

In a staged source archive without `build/`, the new extractor tests (7),
previous EWT exclusion tests (4), English-key tests (2), corpus-preparation
tests (25), no-build registry test (1), and public-ledger tests (24) all passed
without skips. Both old and new static exclusion checks passed. The historical
text-boundary verifier also passed with its isolated archived helpers. The
README path check and its 13 tests passed. The temporary archive was removed.

The pinned SCOWL source archive additionally contains the public 5desk word
list, whose exact member SHA-256 is
`bf400f974c3716bb9f427b583d6e1cade92c283c9a7bfd1b2e10c3ca2bd95464`.
Intersecting it with the same source-verified EWT lemmas added 84 exact keys
from 162 token rows, outside both earlier entries. Two independent extractions
and registrations were byte-identical; all 208 prior entries and coverage
metadata were preserved. The new fixture SHA-256 is
`a5b984e703bd6ab49c72906da4bbea2c5269d3e80454292c82c0ac2d64c1bfd1`.
SCOWL's complete constituent notices remain in the existing project notice.
These hashes are public and reversible, not anonymization; unknown forms,
English morphology and independent qualification remain incomplete. The
public source downloads and generated registration files were removed.
Four focused tests passed, including a real `new-families` overlap gate that
did not match before this entry; the 24 public-ledger and 25 corpus-preflight
tests passed. In a staged source archive without `build/`, the four new tests,
the no-build registry test and both old and new registration checks passed.
An initial incomplete archive omitted the packaged trie and failed; it was
discarded and the test repeated with the required source assets. Hosted CI was
not run for this addition.

At commit `42f67fdd`, a separate clean Git checkout with the pinned llama.cpp
submodule and no initial root `build/` passed the complete standard-library
profile: 179 modules, 883 tests and no failing modules (Python 3.14.6 on
macOS). The isolated historical text-boundary checks and both the new SCOWL
registration check and its 84-key count also passed in that checkout. The
temporary checkout and test outputs were removed. This is not hosted CI,
device evidence, or a complete English-family qualification. The earlier
claim of zero skips was withdrawn: the summary read `skips` instead of the
receipt's `skipped` field, and the temporary receipt was removed.

The pinned FrequencyWords 2018 full English list (19,977,552 bytes; SHA-256
`7fea67ab954e2c01df6c608c9826e594cf36f8823b3243554f88245fb75dc506`)
adds 845 exact public EWT lemma keys from 1,623 token rows after the preceding
three exclusions. The preselected minimum count of five filters one-off terms;
it is not a quality or independence threshold. Two extractions were byte-identical
with fixture SHA-256 `b7d11b0d6f56f3c04f4f5583131577ae1f02507f011c19a05fdef86f6e2f6263`.
FrequencyWords attribution and CC-BY-SA-4.0 content terms are preserved in the
existing project notice. Public unsalted keys are reversible; no source
sentences or identifiers are retained. No morphology is inferred, and English
coverage and independent qualification remain incomplete. The static checker
verifies registered bindings without re-extracting the source.

The strict family-disjoint preflight also has a separate mandatory EWT surface
fixture: 16,913 exact normalized annotated token forms from 216,055 integer
token rows, SHA-256
`3a70fef09c85a7cdf08da6c43c65bfacfb859de67dd971c04a8f80b29f0ecc4e`.
It checks both typed and expected English surfaces and refuses a match, without
calling those forms lemmas or treating them as labelled controls. CoNLL-U token
forms may differ from whole original source words. The `new-sentences` profile
does not apply this extra rule. Two source-locked extractions produced identical
fixture bytes. The public EWT source is CC-BY-SA-4.0; hashes are unsalted and
reversible. The input wrapper binds the fixture, helper, and source lock, while
the selector guard snapshots and rechecks them before accepting a proposal.
Neither English family completeness nor source/label/model qualification is
established, and the historical lexical and control registry entries remain
unchanged.

The staged source archive without `build/` passed four fixture/gate tests,
25 public-preparation tests, 22 text-preflight tests, 20 selector tests and
the static fixture check. Ten historical model-fixture tests and the isolated
historical boundary checks also passed locally. A first archive run failed
because the new test row had the wrong partition; the corrected full archive
run passed. Temporary downloads and source archives were removed. Hosted CI
has not been run.

Follow-up: the separate no-build registry test initially failed after the
surface module was introduced, because its minimal copied source list omitted
the new helper, fixture, importer, and lock. That isolated copy now includes
all four and additionally verifies that an English `new-families` surface match
is blocked. The corrected test passed. The earlier 71-test archive run did not
include this minimal-copy test and should not be read as covering it.
Two generated registries were byte-identical and preserved all 209 preceding
entries and coverage metadata. In a staged source archive without `build/`,
the new tests (4), no-build registry test (1), public-ledger tests (24), and
corpus-preparation tests (25) passed. The new and two prior static checks
passed; test inventory validation reported 180 standard-library modules.
The public test lemma `suckup` was rejected by the new-families overlap gate
only after registration. Temporary source downloads and the staged archive were
removed. Hosted CI and independent English qualification were not run.

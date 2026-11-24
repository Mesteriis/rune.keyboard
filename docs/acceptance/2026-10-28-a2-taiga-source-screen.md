# A2: Russian Taiga source screen

## Early historical unknown-word cross-check

The 3,400-row early RU qualification-v2 file matched its historical ledger
parent's SHA-256. Its already-quarantined unsupported keys correspond to 171
rows and 171 distinct NFC/casefolded target surfaces (73 correct controls and
98 typo targets). Two separately downloaded, hash-verified copies of the
already-disclosed Taiga dev partition were scanned by exact NFC/casefolded
CoNLL-U integer-token surface. Both scans found 15,624 token rows and **zero**
matching surfaces. Thus this Taiga partition supplies no direct annotated lemma
for these historical unknowns under this exact-match method. This does not
prove that their families do not occur elsewhere or that inflected forms are
protected. No guesses, registry changes, target words or source texts were
retained; this partition was already disclosed in the registry.

The [UD Russian Taiga repository](https://github.com/UniversalDependencies/UD_Russian-Taiga/tree/d1e48cd29c1f19b6aad1aec361d9f724db764f66)
identifies multiple public genres, including social text, blogs, fiction, news
and Wikipedia, and declares CC BY-SA 4.0. The inspected development partition is
from tag `r2.18`, commit `d1e48cd29c1f19b6aad1aec361d9f724db764f66`; its
`ru_taiga-ud-dev.conllu` SHA-256 is
`91e8be6f74afd91623500d73954c5595db51a2eb3c7b0e02e38fb3b2508b1b6f`.
The file is kept under ignored `build/` and is not included in the product.

An aggregate read found 1,260 `# text` lines and nine `# newdoc` markers, none
using the EWT importer's `# newdoc id = ` syntax. Seventeen individual text
lines contain at least 300 Unicode code points; none reaches 600; the longest
has 497. The count does not establish whether adjacent sentences form a faithful
natural input context, whether document boundaries can be identified reliably,
or whether any passage is independent of previous training/evaluation data.
No model was run and no sentence is claimed as a fresh holdout.

The inspected development partition is now imported into the holdout ledger
as an exposed source: 1,260 rows produce 1,244 unique normalized sentence keys,
five already present in the compatible full-sentence namespace. The document,
family and context axes remain explicitly missing; the separate control ledger
does not support this source. The sentence keys reject exact normalized overlap
with compatible Tatoeba/EWT keys, but do not establish broader corpus independence.
Do not use this partition as a fresh evaluation source. The other partitions
have not been read for this screen. Corpus licensing and source overlap must be
checked before redistributing or admitting a derivative into a qualification
dataset.

## Dictionary and surface exclusions

The inspected dev source was subsequently scanned for all Cyrillic fragments
in its 1,260 public `# text` sentences. The pinned dictionary-only Pymorphy
backend supplied every available analysis, producing 4,528 distinct family
keys; 652 were absent from the preceding lexical registry. All 6,185 distinct
fragments of at most 32 characters are also stored as exact surface exclusion
keys, including 297 without a dictionary analysis; 6,018 exact keys were new.
Two overlong fragments are counted but remain outside that exact-surface
namespace. Extracting fragments is conservative and can include components of
compound or mixed-script text; it is not a claim that each is a complete word.

The family/surface fixture stores hashes, not source sentences, and is bound to
the existing sentence-only parent and the pinned public source lock. Those
unsalted public hashes are reversible by enumeration and are not anonymization.
The dictionary identity covers the stable files in the existing Pymorphy
receipt, excluding generated `RECORD` metadata; wheel hashes remain pinned in
`tools/morphology/requirements.lock`. Full native/runtime supply-chain
attestation is not claimed. Two separate hash-locked Python 3.12 environments
regenerated the same fixture bytes. An earlier attempt using the complete
installed-package receipt produced the same keys but a different receipt hash
because `pymorphy3`'s generated `RECORD` varied; that attempt is not counted
as a byte-identical full fixture.

Real preparation preflight now rejects a newly excluded source surface.
The fixture check, source-identity/mutation tests and test inventory are wired
into CI. Document IDs, source contexts, non-Cyrillic/overlong forms, the
control registry's Taiga source representation, global completeness and fresh
qualification remain open. No model or APK changed. Temporary public source
and environments were removed after verification.

## Within-sentence source-context exclusions

The pinned dev file was scanned again for Cyrillic fragments in the 1,260
source `# text` sentences. For each of 12,992 occurrences, the preceding
128-character sentence context and the token were recorded in original and
casefolded form. This adds 20,464 previously absent regression-control keys
and 12,059 previously absent lexical context keys. The source can contain
compounds and mixed-script words, so fragment extraction is conservative and
does not assert tokenization, labels or typing intent. Prefixes do not cross
sentence boundaries; other context forms remain possible.

The source-bound fixture contains only unsalted hashes; those are not
anonymization of public text. Python 3.12.14 and 3.14.6 generated byte-identical
fixtures. Two independent registrations preserved all previous registry entries
and incomplete-coverage flags. A previously unprotected source context is now
rejected by both registries; corruption and parent/source bindings are tested.
The source has seven `# newdoc_id` markers and two unnamed `# newdoc` markers;
this does not establish stable document identity for all nine source segments.
Document boundaries, cross-sentence contexts, other corpus sources and fresh
qualification remain open. No model or APK changed; the temporary source file
and registration files were removed. Hosted CI was not run.

## Annotated-lemma exclusions

The source's CoNLL-U annotation contains 15,624 integer-token rows. Of these,
12,603 carry an annotated lemma consisting of 1–32 Cyrillic letters; they
contain 4,080 distinct casefolded lemmas. All 4,080 were added as exact
surface keys, including 2,242 keys absent from the prior registry. The
hash-locked Pymorphy dictionary recognized 3,931 of those distinct lemmas;
all its analyses produced 4,216 family keys, of which 17 were new. The other
149 eligible lemmas remain exact-only. The remaining 3,021 token rows have
lemmas outside this narrow form and are not claimed covered by this addendum.

UD's [source description](https://github.com/UniversalDependencies/UD_Russian-Taiga/blob/d1e48cd29c1f19b6aad1aec361d9f724db764f66/README.md)
describes the dataset as samples extracted from multiple collections; neither
file order nor the nine document-marker groups is sufficient evidence of
continuous original documents. No cross-sentence document identity or
synthetic cross-sentence text is asserted. Source annotations are used as
public exact forms; only actual dictionary analyses are assigned to the
Pymorph family namespace. This is not independent qualification.

Two separately installed, hash-locked Python 3.12 environments regenerated
the fixture byte for byte. The dictionary identity follows the preceding
family addendum and excludes the installer-generated `RECORD`. Source and
fixture corruption, exact exclusion and all-dictionary-analysis behavior are
tested. Earlier entries and incomplete coverage were preserved; the temporary
source and environments were removed. No model or APK changed.

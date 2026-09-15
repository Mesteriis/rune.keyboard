# Packaged Russian dictionary guard

The app packages `ru.morph`, a public-data derivative of OpenCorpora 0.92 /
revision 417150 from the pinned morphology environment. It contains 3,063,710
exact word forms in 28,591,430 bytes, with 69,078 forms explicitly marked as
having multiple lemma families. It contains no user text and uses no corpus
frequency or predicted forms. OpenCorpora attribution and the CC BY-SA 3.0
license link ship in `notices/OpenCorpora-CC-BY-SA-3.0.txt`.

## Reproduce

From the project root, after installing `requirements.lock` as documented in
[README.md](README.md):

```sh
PYTHONDONTWRITEBYTECODE=1 build/morphology-venv/bin/python tools/morphology/export_dictionary.py --output app/src/main/assets/smarttyping/lexicon/ru.morph --manifest app/src/main/assets/smarttyping/lexicon/provenance/morphology-manifest.json
PYTHONDONTWRITEBYTECODE=1 build/morphology-venv/bin/python -m unittest discover -s tools/morphology -p test_export_dictionary.py
```

The manifest binds installed package files and exporter content; no machine paths
or timestamps are recorded. Export uses the dictionary's exact DAWG records and
normal-form/paradigm identity. It excludes non-Russian, non-NFC, uppercase, and
longer-than-32-scalar records. It does not expand е/ё spelling variants. A family
is not a semantic disambiguation: homonyms sharing spelling and paradigm remain
indistinguishable. Multi-family words have no usable lemma ID.

## Runtime and automatic admission

`AndroidMorphologyLexiconLoader.load` requires a worker. It opens the uncompressed
APK region, maps immutable bytes, validates the pinned entire-file SHA-256 and
internal checksum, then publishes a read-only `MorphologyLexicon`. Missing,
compressed, corrupt, cancelled, and main-thread loads return `UNAVAILABLE`.
Validation uses 16 KiB scratch; it never builds a whole-dictionary heap map.
Lookups binary-search front-coded blocks and decode at most 32 block records
plus one record per binary-search step. Per-query buffers hold at most 64 UTF-8
bytes; they are cleared after lookup and never retained. Mapped pages are
reclaimed by the runtime; descriptors are closed immediately after mapping.

`AutoCorrectionAdmissionGuard` only adds vetoes **after** existing automatic
qualification. Suggestions remain available. Russian source membership protects
rare correct words such as `почтений`, even if absent from the ranked dictionary.
Unavailable dictionary evidence and unknown/ambiguous winner analyses veto.
A competing candidate at weighted edit cost no more than the winner plus 0.25
must have the same known lemma family; otherwise automatic action is vetoed.
The 0.25 band is a conservative implementation threshold, not calibrated
confidence. Frequency cannot resolve ambiguity inside the band. All complete
local candidates and visible candidates are checked, including candidates omitted
from the displayed strip. Existing source completeness and eligibility gates
remain the caller's responsibility. Canonical case-only spelling identity and
non-Russian automatic paths retain their existing policy ownership.

This guard does not establish grammatical intent among inflections of one family,
does not certify the complete natural-language dictionary, and does not demonstrate
Android correction quality. Off-main loading still needs device timing and APK
size measurement. Lookup is bounded and does no filesystem reads, but initial
mapped-page faults can occur after publication.

# Role-feature parity data

These are authored test inputs and dictionary-derived data, not user text,
training labels or a qualification corpus. `vectors.tsv` contains 5,472 Python
reference cases for the 15 role features and the preceding-word boundaries.
The fifth TSV field uses `-` for an empty preceding-word list; other lists are
UTF-8 space-separated words encoded with base64.

`grammar.bin` and `past.bin` are small query-specific fixtures.
`full-past.gram` contains 127,220 dictionary query spellings with only known
past-finite verb analyses. It uses the existing front-coded grammar format;
its semantic purpose comes from the pinned exporter and receipt, not a newly
invented tense bit. The current main grammar asset is used separately in tests.

Dictionary data is derived from OpenCorpora contributors through the pinned
pymorphy3-dicts-ru distribution, under CC BY-SA 3.0:
https://opencorpora.org/ and https://creativecommons.org/licenses/by-sa/3.0/.
The changes are selection of dictionary analyses and deterministic packing.
`provenance.json` and `full-past-provenance.json` preserve dictionary versions,
file digests, exporter identity and output hashes. These files are test resources;
they do not add an asset to the application APK.

Regenerate into new build locations with
`tools/typing_experiments/export_right_context_role_fixtures.py --output <new-dir>`
and `tools/typing_experiments/past_context_assets.py --output <new-file.gram>`
using the pinned morphology Python environment. Copy the generated fixtures and
full past index with their receipts, and bind all three dictionary hashes in
`hashes.properties`. The fixture exporter does not create the full past index.

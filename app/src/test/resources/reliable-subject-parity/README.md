# Reliable following-subject parity

The 5,510 cases contain authored suffixes/candidates and Python source-v2
reference vectors. They are not user text, model training or accuracy evidence.
The dictionary fixture derives from OpenCorpora contributors through the pinned
pymorphy3-dicts-ru distribution, under CC BY-SA 3.0:
https://opencorpora.org/ and https://creativecommons.org/licenses/by-sa/3.0/.
The change is selection and deterministic packing of dictionary analyses.
Dictionary versions, file digests, source/exporter hashes and attribution are in
`provenance.json`; `hashes.properties` binds the mini dictionary. Tests repeat
all vectors against the existing full application grammar asset. These resources
are for JVM tests and are not packaged as new application assets.

Regenerate with `tools/typing_experiments/export_reliable_subject_fixtures.py
--output <new-directory>` in the pinned morphology Python environment.

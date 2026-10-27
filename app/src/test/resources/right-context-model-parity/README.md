# Experimental model bridge parity

This is the frozen 178-feature v6 numeric model and authored numeric reference
inputs, not an enabled application model or accuracy-qualification corpus.
`provenance.json` binds the model, Python exporter and dictionary receipt.
The model is trained from authored contrasts with dictionary-derived features;
no owner text is included. The model bytes are in JVM test resources only.

`vectors.tsv` checks 36 composed vectors from controlled synthetic base features.
`runtime-vectors.tsv` checks 36 candidate/fallback/original cases using the full
installed feature assets, including the character model; it contains Python
base/revision vectors and raw/bounded scores. The edit metadata is deliberately
authored numeric input, not a claim that a live candidate search produced it.
`probes.tsv` checks float32 neighbors, exact borders and double-only increments
for all 71 distinct split boundaries in the model (284 probes).

Regenerate into a new directory with
`tools/typing_experiments/export_right_context_model_fixtures.py --model-root
<workspace-build-model-root> --output <new-directory>` in the pinned morphology
Python environment. The full feature dictionaries and past-finite index used by
the tests have their separate attribution and hash receipts.

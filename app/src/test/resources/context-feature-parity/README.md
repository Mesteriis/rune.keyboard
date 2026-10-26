# Public contextual-feature parity fixtures

These small binary tables and vectors test the Python-to-Kotlin feature port. Contexts are constructed examples; they contain no owner messages or evaluation labels used by the runtime scorer.

- Dictionary analyses: OpenCorpora 0.92, revision 417150, via pinned pymorphy3 2.0.6 / pymorphy3-dicts-ru 2.4.417150.4580142. Derived data: [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Source: https://opencorpora.org/. Transformations: dictionary-only lookup including the analyzer's е/ё alternatives, grammar-bit projection with full-analysis ambiguity retained, front coding.
- Wikipedia pair counts: Russian Wikipedia contributors, Wikimedia Wikipedia snapshot 20231101 / `wikimedia/wikipedia` revision `a634f78b1c435397c07001e175fa74cc4ad5e775`. Source metadata: CC BY-SA 3.0 / GFDL 1.3. These count derivatives use CC BY-SA 3.0. Corpus: https://huggingface.co/datasets/wikimedia/wikipedia. Frozen-table denominators are preserved even in the tiny fixture subset.
- Conversational pair counts: Tatoeba contributors, official Russian CC0 sentence subset. [Source and license documentation](https://tatoeba.org/en/downloads), https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_CC0.tsv.bz2. Counts come only from its training partition.

`provenance.json` binds source tables, installed dictionary packages, reference feature code and exporter by SHA-256. `hashes.properties` binds the binary fixture tables. The application does not package these test resources.

Regenerate with the hash-pinned morphology environment and frozen source tables available:

```
build/typing-ranker-v2-venv/bin/python tools/typing_experiments/export_context_feature_fixtures.py --output app/src/test/resources/context-feature-parity
```

The output directory must be new. Preserve existing fixtures before regeneration.

# Wikipedia attribution and transformations

Source: Wikimedia Wikipedia, snapshot `20231101`, EN/RU/ES. Dataset repository: <https://huggingface.co/datasets/wikimedia/wikipedia>. Dataset-card revision: `b04c8d1ceb2f5cd4588862100d08de323dccfbaa`. Parquet revision: `a634f78b1c435397c07001e175fa74cc4ad5e775`.

The exact shard paths, byte counts and SHA-256 hashes are in `source-lock.json`. Cached inputs are `build/smart-typing-0.3/qualification-v4/wikipedia-20231101/{en-0027,ru-0008,es-0006}.parquet`; the actual repository paths are language-specific and recorded individually in that lock. Generated `attribution.jsonl` links every selected row to its article URL/title, article ID, source shard/row and extraction span. Wikipedia contributors are the source authors. The corpus is extracted source material, not newly authored chat text.

Retain the source license metadata and the existing `tools/model/rune-text-0.2/WIKIMEDIA_NOTICE.md`. The pinned dataset card identifies GNU Free Documentation License 1.3 and Creative Commons Attribution-ShareAlike 3.0, with some text available only under the Creative Commons license:

- <https://creativecommons.org/licenses/by-sa/3.0/>
- <https://www.gnu.org/licenses/fdl-1.3.html>
- <https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use>

Recorded changes: article NFC normalization; bounded prefix extraction/truncation at whitespace; prefix whitespace stripping; current-word Unicode casefolding; source punctuation/whitespace normalized to the observed marker plus one ASCII space. Offsets refer to NFC Unicode code points, and the raw article and normalized article hashes are both retained. The future production exporter applies its own bounded sentence-start casing when constructing punctuation alternatives.

Per-article attribution accompanies every corpus copy. The host-side corpus and parquet inputs are not Android application assets. No source excerpt or selected row is printed by the generator or validator.

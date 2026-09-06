# Wikimedia Wikipedia training-source notice

Rune Text 0.2 uses a bounded, reproducible sample of the Wikimedia Wikipedia
dataset snapshot `20231101` solely to prepare host-side spelling-ranking
training pairs. No Wikipedia text or parquet file is packaged in the Android
application.

Dataset repository: <https://huggingface.co/datasets/wikimedia/wikipedia>

Dataset-card revision: `b04c8d1ceb2f5cd4588862100d08de323dccfbaa`

Parquet conversion revision: `a634f78b1c435397c07001e175fa74cc4ad5e775`

The dataset card states that original textual content is licensed under the
GNU Free Documentation License 1.3 and Creative Commons Attribution-ShareAlike
3.0, with some text available only under the Creative Commons license. The
exact source files, byte sizes, and SHA-256 digests are recorded in
`source-lock.json`.

License texts and terms:

- <https://www.gnu.org/licenses/fdl-1.3.html>
- <https://creativecommons.org/licenses/by-sa/3.0/>
- <https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use>

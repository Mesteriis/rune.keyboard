# Q5 subtitle source screening

The [Russian Spellcheck Benchmark](https://huggingface.co/datasets/ai-forever/spellcheck_benchmark)
describes two-stage human correction/validation, and its card declares MIT for
the benchmark. Its sources include copyrighted and potentially sensitive
material; this screen used only its separately stored subtitle train/test files,
not the medical or social-media subsets. The underlying subtitle rights and
suitability for redistribution have not been independently verified.

The pinned revision and both Git blob identities were verified against the
exact downloaded bytes. Each split contains 1,810 sentence pairs. For the
review's lowercase 2–6 Cyrillic word filter with only optional final punctuation:

| Split | Exact unchanged source/correction pairs | Eligible corrected phrases | Eligible unchanged phrases | Words in eligible unchanged phrases |
| --- | ---: | ---: | ---: | ---: |
| Train | 647 | 83 | 32 | 129 |
| Test | 665 | 76 | 35 | 150 |

One case-folded, whitespace-normalized corrected sentence occurs in both
splits. The unchanged pair count is not a proof that a sentence is error-free;
it records exact equality after the dataset's annotation. Subtitles are scripted
speech and do not establish actual keyboard-message frequencies. These numbers
are insufficient for the requested 3,840-control baseline under the chosen
filter; they are not a false-change estimate or an independent qualification.

The [numeric receipt](2026-10-29-q5-subtitle-source-screen-evidence.json)
contains only counts, hashes and source identity; two independent local runs
matched byte for byte. The source files remain only under ignored `build/`, with
no raw text or per-row fingerprints placed in the repository or ledgers.
No model or keyboard was run on this material. The existing incomplete Q6
registry and upstream-rights checks must be resolved before considering it for
any released or independent corpus. Unit tests cover strict shape, filter,
cross-split comparison and the no-text output invariant.

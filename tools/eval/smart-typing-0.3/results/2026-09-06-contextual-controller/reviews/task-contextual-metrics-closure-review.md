# Contextual metrics and compile-closure rereview

**Scoped verdict: PASS for prior findings 1 and 3.** No residual gap was found in these two fixes. This is not approval of the full contextual attribution tool: prior finding 2, covering production route/readiness/reply preconditions and secondary routing reasons, remains intentionally outstanding.

## Finding 1: failure-path metrics — closed

`build_metrics()` now:

- enforces the ordered bounds `0 <= tapSuccesses <= tapAttempts <= offers <= rows`;
- counts abstentions directly as known rows with no offer, so a harness-error row cannot be subtracted both as an offer and an indeterminate row;
- marks missing tap attempts and unsuccessful taps incomplete, together with unresolved rows, harness errors, forbidden edits, and unsolicited edits.

The regression at `test_contextual_controller_attribution.py:150-174` covers an ordinary unattempted offer and four harness-failure positions: before tap, refused tap, handled tap, and duplicate tap. It requires preserved row/offer/error counts, one known abstention beside the failed row, nonnegative full-denominator rate evidence, suppressed complete agreement, and `attributionComplete=false`.

Preserved evidence is coherent:

- `review-metrics-red.log`, SHA-256 `9859b2a40b788a7060ce3a32046ec40eacbc1723c7e5442c1370458ad12ba6f6`, records the former `ACTION_COUNTS` exceptions and incorrect abstention counts.
- `review-metrics-green.log`, SHA-256 `5abb1f88e51572c706b914a4c6b58ff1630a0d28daa87709f75fb9cd8d4b34e3`, records 28 passing tests after the metric fix.

## Finding 3: explicit compile-source closure — closed

Compile source selection is now owned by the new tool. `COMPILE_SOURCES` explicitly enumerates the 39 inherited production sources; `compile_inputs()` explicitly adds the eight contextual dependencies and two host sources, deduplicates them, and requires all 49 files to exist. It no longer reads the archived dot-fix command receipt to choose sources or classpath entries.

The archive remains in `bind_runtime()` only as hash-bound provenance/comparison evidence. Mutating its content cannot alter `compile_inputs()` selection. The regression at `test_contextual_controller_attribution.py:207-217` makes every `read_json()` call fail while exercising `compile_inputs()`, then requires exactly 49 unique existing sources and the current host entry point.

Preserved evidence is coherent:

- `review-source-closure-red.log`, SHA-256 `eb37f45167c8a5a6b3416bb7863fc2f995f039979b4b09e9de6bea932b865bae`, shows the regression detecting the former active archive read.
- `review-source-closure-green.log`, SHA-256 `70ef8403d3d822976a7a679272eaf45bcc6a98e79a4e5c3c9165a88badf8cd9c`, records all 29 tests passing.

Reviewed source identities:

| File | SHA-256 |
|---|---|
| `contextual_controller_attribution.py` | `6fb5574115f414f1e73b1a782f70ad4ddc8cbe1298c6e7d80bca15a0a8b407fb` |
| `test_contextual_controller_attribution.py` | `d07f84d87e0077648c5fc2608a4be3c700ce86acb282274ccaa5cfbc4e1b4007` |

This rereview was read-only apart from this report. It ran no tests, Gradle, device operation, model call, numeric corpus replay, scoring, network access, or source edit.

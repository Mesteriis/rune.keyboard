# Combined ranking calibration and Kotlin port — 2026-09-03

Baseline `10064a88442558f6dd5285733d066a03c6d4cd57`. This slice implements
the pure Kotlin ranking calculation and calibration evidence for PR7. It does
not enable automatic correction or change the production candidate width.

The exact Rune Text GGUF completed all 2953 actual-candidate calibration
requests; 3047 original-only rows need no model call. Cache digest and request
identity were independently revalidated. There are 2944 successful responses
and nine `SCORING_FAILED` results (RU seven, ES two). A vocabulary-only native
probe of all nine errors and three successful controls confirms zero divergent
span in every failed set and none of the controls. Such sets must refuse model
ranking under the contract; they remain in the deterministic fallback and report
denominators. No generated text or user payload is archived.

The combined policy subtracts the model-weighted difference between candidate
and original average log probabilities from the deterministic penalty. Both
the original penalty and runner-up margin must pass. A declared 43200-point
grid per language selects parameters on calibration only. All selected model
weights are one. The deterministic fallback configuration remains fixed.

| Language | Replacements | Correct | Precision | Wilson 95% | False changes /1000 | Coverage /2000 |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| EN | 347 | 344 | 99.14% | 97.49–99.71% | 0 | 17.35% |
| RU | 357 | 354 | 99.16% | 97.56–99.71% | 0 | 17.85% |
| ES | 434 | 430 | 99.08% | 97.65–99.64% | 0 | 21.70% |

All replacements in this run used model evidence; fallback abstained on the
failed sets. These are ideal-availability calibration counts on correlated
authored rows, with descriptive row Wilson intervals. They do not establish
holdout precision, real boundary availability, energy use or release readiness.
The existing failed prepared-candidate holdout remains untouched.

`CandidateRanker` validates bounded candidate IDs, finite nonpositive raw scores,
positive token counts, feature bounds and retrieval vetoes before calculation.
Its 6000-row numeric fixture compares every deterministic and combined decision
with the independent Python implementation. Additional tests cover malformed
scores, overflow, ties, minimum code-point length and immediate reuse after a
rejected request. It has no model execution, persistent state or editor access.

Validation: Python 19/19 PASS; targeted Kotlin 4/4 PASS; fresh root JVM 602/602
PASS with zero failures/errors/skips; all prescribed local lint, debug/release/
profile, privacy, dependency, IME and native-symbol gates PASS (248 tasks).
CI now explicitly discovers the pipeline Python tests without requiring a model.
Remote CI for this revision is unrun. Mandatory post-commit JVM is reported
against the resulting commit.

API26/API37/Fold integration of this kernel is UNRUN; earlier device checks
cover earlier slices. The requested phone installation is BLOCKED: the latest
ADB inventory contains only two emulators. No APK was installed in this slice.
The current debug APK SHA is
`70002b8032aee14fffca48e030820f5f945a7220da8d3cd773b8fbbc9a34fb4d`.

Controller integration, full automatic correction Undo, contextual punctuation,
the frozen final product holdout, complete Fold/energy matrix, external CI and
model publication remain open. Version remains 0.2.0; no push or remote PR.

Evidence: `tools/eval/smart-typing-0.3/pipeline/results/2026-09-03-combined-calibration/`.
Numeric Kotlin controls: `app/src/test/resources/smarttyping/ranker/`.

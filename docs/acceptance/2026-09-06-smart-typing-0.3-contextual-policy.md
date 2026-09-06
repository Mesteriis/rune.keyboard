# Contextual punctuation score correction — 2026-09-06

Development correction based on `fd8872f`; **release qualification remains open**.
Dividing a negative log-probability sum by differing token counts can favor an
added punctuation token even when its total probability is lower. The pure
`ContextualPunctuationPolicy` now compares sums, requires an advantage greater
than0.5 over Original and at least4.0 over the next punctuation alternative,
and abstains on invalid numeric/ID contracts or insufficient evidence.

The controller still validates session, revision, request and candidate ownership.
A successful numeric result only exposes an existing suggestion; an explicit
selection is required for the existing bounded editor replacement. Spelling
ranking and native scoring are unchanged.

The margins were selected using the archived calibration split. The
[calibration diagnostic](../../tools/eval/smart-typing-0.3/pipeline/results/2026-09-06-contextual-calibration-diagnostic/README.md)
does not open the held-out score cache. Its authored contexts repeat, so its
counts cannot establish unseen performance. Freeze the new source/configuration
before evaluating a new unseen holdout; do not retune against that holdout.

Verification before commit:

- Regression tests against old arithmetic:6 tests,3 expected failures; extracted
  kernel against old arithmetic:18 tests,12 expected failures.
- Corrected scoped JVM:181/181; full `testDebugUnitTest --rerun-tasks`:707/707,
  with zero failures/errors/skips.
- Prescribed lint, debug/release/profile, privacy, intelligence-boundary,
  dependency and native-symbol gates, plus Android-test APK build:PASS.
- Independent review of the exact four-file policy patch:spec and code quality
  PASS; patch SHA256 `0ccaf283d1016ab1e25d3a205fbfd46f0eb24d7b382bb934b9a562fc5047478a`.

Numeric verification receipts and compressed logs accompany the calibration
diagnostic. Newly built Android tests have not run: updating the physical phone
is blocked by a different installed debug signature, with a verified local
model/settings backup and user confirmation pending. Old installed-APK passes
do not verify this policy. Version remains0.2.0; no main merge or release claimed.

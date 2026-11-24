# A1: manual English `i` suggestion, automatic rule still open

The English active layout now generates `I` as a manual-only canonical-case
suggestion for the exact valid token `i`. The one-letter uppercase exception is
accepted only for that exact English pair with both automatic and unambiguous
flags false. It does not change global case analysis or grant automatic
eligibility. Spanish and Russian active layouts do not get this special
candidate, and `I`, `ii` and `i'` are not changed by this path. The suggestion
can appear in an ambiguous context such as `chapter i`; the user must choose it.
This does not implement or qualify A1's requested automatic conversion.

Four disclosed host probes ran twice: `yes i` offers `I` and remains `yes i`
after space, Spanish `si i` stays literal without `I`, `chapter i` remains literal
with a manual `I` option, and `yes ii` remains unchanged. Both 2,160-row and
12,000-row Q7 regression baselines matched on two runs. All 1,378 JVM tests
passed, including manual choice, boundaries and layout controls.

On API 26 and 37 emulators the real IME showed `I` without the auto-preview
arrow, kept `i` after space, accepted an explicit tap, and did not offer the
special suggestion in Spanish. Two methods passed per API. The initial API 26
run failed an incorrect test assumption that a selected suggestion must mean
automatic replacement; the corrected test checks the visible text and actual
space result. Both task-owned emulators were stopped and deleted. Raw logs:
`build/review-a1-manual-api26-20261028/native2.log` SHA-256
`e3e44f6c1ee337480c55b16a57f8855a80f8cb63c9509495eceaad654c0f3052`, and
`build/review-a1-manual-api37-20261028/native.log` SHA-256
`3784748865585d19e4044cf5ffc237c8fc32fb92f49a439395af06e4d9a82143`.
Debug APK SHA-256 `c29cde8adb3a7cc7db9e329a0ae61a427f736997609c5962d611abdb38478015`.

Automatic behavior, versioned qualification, fresh natural holdout including
Roman numerals/code/Spanish/abbreviations, and Fold tests remain outstanding.
The clean-source `:app:privacyGateRelease` passed at commit `38fc692`;
its local log is `build/review-a1-manual-privacy-20261028.log`.

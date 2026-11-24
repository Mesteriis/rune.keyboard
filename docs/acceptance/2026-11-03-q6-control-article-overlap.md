# Q6 control source identity overlap

`control_ledger.assert_disjoint` now rejects a disclosed article or Tatoeba
sentence identity when the proposed row supplies it, even if the word and
context are new. Missing source identities remain supported for standalone
controls; malformed supplied identities are rejected. The control ledger
still cannot certify freshness and remains explicitly incomplete.

The named-regression source check also bound the old control helper. It now
runs with the two historical text registration checks using the isolated,
hash-verified archived helper. Those checks retained their original registry
entries and verified all 56 named rows, 179 shared-text occurrences and 470
all-text occurrences against the changed live helper. The initial broad test
run found the named check's dependency; it is preserved in the isolated CI
runner, not discarded. The temporary runner resolves its path before invoking
the historical script, including on macOS where `/var` resolves to `/private/var`.

Final validation: 818 standard-library tests in 168 modules passed with zero
failures, errors or skips; the receipt SHA-256 is
`48fe7636748c1f5a36091785a6ad3379c8b86018fc38ae91eae2adb293c75b99`.
The two historical runner tests and 12 authored-registration tests passed.
An archive of staged sources without `build/` passed the isolated historical
checks. Seven other registration checks passed on a prior disposable archive
with both old helper files modified. Hosted CI was not run.

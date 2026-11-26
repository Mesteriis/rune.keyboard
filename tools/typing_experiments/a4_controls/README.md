# A4 authored boundary discovery controls

`controls-v1.jsonl` is an authored, public, non-personal regression set frozen
before this run: 54 abbreviation candidates, 43 synthetic Cyrillic domain-label
inputs and 43 list-heading inputs. It includes the five abbreviations named in
the review, which were already replayed in the earlier five-item discovery probe.
Domain-label entries are plausible input strings, not claims that
the corresponding domains exist. The categories and preserve labels are test
intent, not a frequency-weighted corpus or verified ground truth for every
context. Each is replayed at an empty prefix with space, period and colon.

Its contexts and surfaces are recorded in `../control-ledger.json` so future
qualification cannot treat them as fresh. The set is for finding regressions;
it does not independently qualify an automatic correction policy.

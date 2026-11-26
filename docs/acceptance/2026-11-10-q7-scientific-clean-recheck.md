# Q7: clean scientific-profile recheck

A clean temporary checkout at `6b4e9c6e`, with the pinned local submodule and a
Python 3.12 environment, completed the scientific CI profile. All 25 modules
reported: 97 tests, zero failures or errors, and one skip in
`tools/typing_experiments/test_word_ranking.py`. The profile returned PASS; the
skip is not a passed test. Dependency installation, the backend gate, historical
data fixture tests and restoration, source fixture tests and checks, model
fixture tests and checks, and word-ranking fixture tests also returned zero.

The tracked checkout remained clean and the temporary checkout and environment
were removed. This was a local run, not hosted CI, and does not resolve the
missing v6 historical inputs or establish release approval.

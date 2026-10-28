# Q2: packaged provenance repository references

This scoped follow-up to `4c2443b` retains the exact pending compact cascade
policy at its already-declared path. Its SHA-256 is
`5057e9e955fafdc507e06b4b1e88307b4dd2201d6864a9620b39e23358a33acd`, matching
both packaged provenance and CompactAutoCorrectionPolicy.POLICY_SHA256.
Policy bytes, application code, thresholds and assets are unchanged.

The eight trainingScripts entries in experiment provenance identify seven
current files byte-for-byte. The eighth identifies the original
`test_refinement.py`, before portable fixture integration in `29e84b4`.
The exact original blob was recovered using
`git show 79868bd:tools/typing_experiments/test_refinement.py` and independently
SHA-256 checked against the shipped digest. It is retained under
`tools/typing_experiments/historical_provenance_sources/`, with a digest-bearing
filename. The current portable test remains unchanged. The historical source
is read as bytes by the checker, never imported or executed by it.

`python tools/check_packaged_provenance_paths.py` passes for all eight packaged
`*provenance.json` files under app assets: seven explicit repository references
and eight training-script identities. Tracked missing metadata and new untracked
metadata are both checked, as are symlink escapes, traversal, script drift and
policy hashes. Git membership is read from the index via `git ls-files`.
The current patch adds this check to the stdlib CI job.

All ten regression tests pass on Python 3.12.14 and 3.14.6:
`python -m unittest discover -s tools -p test_packaged_provenance_paths.py -v`.
This proves explicit packaged repository paths and declared trainingScripts
identities. Dataset-relative paths, remote repository names, unnamed script
hashes, transitive training dependencies, README commands, model execution and
fresh qualification are separate requirements. Q2 and Q6 remain in progress.
No new Android installation or hosted CI run was performed for this source-only
slice. Existing pending owner changes outside the selected files are preserved.

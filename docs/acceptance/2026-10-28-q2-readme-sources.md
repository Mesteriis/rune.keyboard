# Q2: README source paths and historical navigation

This slice follows `9bf6d64`. It integrates the pending experiment README sections
after their referenced source scripts/tests were retained and checked in the
preceding slices. The old refinement metric table is now explicitly historical:
it does not qualify the later augmented/abstaining bundled ranker. Current test
instructions point to the actual Python 3.12 CI profiles and isolated runner,
rather than a machine-local environment that no longer exists. Historical model
commands still require their original pinned inputs and recorded runtimes.

Three referenced reports (joint short/long, grammar-context experiment and local
stress audit) are retained with their original bodies and separate historical
scope notices. This is source/navigation preservation, not a new model, Fold or
independent-data qualification. Their raw pre-integration hashes are retained in
the evidence. Other guide/report navigation and Q6 gaps remain separate work.

`python tools/check_readme_sources.py` checks the main and experiment README:
literal local Markdown paths, explicit project paths, Python source filenames
and named unittest modules must resolve within the checkout and belong to the
Git index (directories must contain indexed files). Missing files, untracked
scripts, path escapes and external symlinks fail. Referenced Gradle output
artifacts are recorded separately without being represented as tracked-source
passes. An explicit Python source under build/ still requires retention.

The checker is deliberately bounded: it does not execute build/training
commands, validate generated datasets/binaries, verify remote links, validate
Markdown anchors or establish transitive model lineage. Thirteen regression tests
pass. The stdlib CI job invokes both the source checker and its tests; hosted CI
has not been run. No app source, asset, production policy or phone state changed.

The final audit checks 65 distinct source/link paths and separately records
two generated Gradle output paths. All thirteen tests pass on Python 3.12.14
and 3.14.6. Guide-fact and packaged-provenance gates, exact test inventory and CI
YAML parsing also pass. The wider app/test suite was not repeated for this
documentation/source-presence slice.

Clean source `475d2af` passes the same source/link audit and all 13 tests. Its
audit JSON exactly matches the primary checkout. Guide facts and the exact
113-stdlib / 19-scientific inventory also pass; the clone's tracked tree is
clean before and after. This is local verification, without hosted CI.

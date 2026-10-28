# Python tools test inventory

Q7's scope is all tracked `test_*.py` modules directly under
`tools/typing_experiments` and `tools/morphology`, plus
`tools/test_qualification_artifacts.py`. The versioned inventory assigns all
103 modules to runnable jobs: 92 stdlib and 11 scientific modules. The retained
`historical-artifacts` profile is empty; the runner's own tests require it to
stay empty. An empty profile cannot produce a successful run.

```sh
python tools/ci/python_tools_tests.py --check
python -m unittest discover -s tools/ci -p 'test_*.py' -v
python tools/ci/python_tools_tests.py --profile stdlib --output build/python-tools-stdlib
python -m pip install -r tools/typing_experiments/requirements.txt
python tools/ci/historical_data_fixtures.py --install-build build
python tools/ci/historical_model_fixtures.py
python tools/ci/python_tools_tests.py --profile scientific --output build/python-tools-scientific
```

Use Python 3.12 and fresh output/data directories. Each module runs in a separate
interpreter; generic imports cannot leak across modules. PYTHONPATH/PYTHONHOME
are removed. Logs, exact child exits, counts and skips are retained and uploaded.
Failures, timeouts and empty suites fail; later modules still run. Inventory
drift or moving modules back into an unwired historical profile fails CI.

## Original historical tests

The three formerly artifact-dependent modules now use explicit class-scoped
resource roots. Their ten original test methods and assertions are unchanged.
No production validator is modified and no historical test is skipped.
`historical_test_fixtures.py` delegates to the versioned fixture reader, which:

- Verifies the fixed archive, original reference CBM/weight identities, public
  source manifests, per-file hashes, article attribution and durable exclusions.
- Restores raw rows, observations, reference models and decoded weights unchanged.
- Creates a fresh temporary source snapshot for each required historical profile.
  All 71 directly declared project-source versions remain hash-bound; 29 changed
  versions are archived, and unchanged files are verified in the repository.
- Rebases only receipt/log/source-map path templates and recomputes their metadata
  hash edges. External compiler/runtime references remain unavailable metadata;
  no dummy runtime files are created and no archived code is executed.
- Removes temporary workspaces and restores resource roots after each class.

The word fixture validates all 9,000 original rows and prior data identities.
Their 8,991 distinct normalized target contexts now have a permanent exclusion
addendum; the original 4,920-article exclusions remain intact. Canonical families
and full source sentences remain unproven; Q6 global coverage is still false.

The new archive is 4,643,389 bytes, includes titles/history attribution for all
4,920 word-corpus articles, and preserves 31 reference/data files (only metadata
paths and their hash edges are transformed). Core public text attribution and
original manifests remain in `historical-data-v1`. Archive generation requires
the original local build and pinned public parquet; normal tests require neither.
See [the acceptance receipt](acceptance/2026-10-28-q7-portable-model-fixtures.md).

## Remaining evidence

The Linux scientific job retains one explicit MLX-only gradient-test skip. Its
supported Apple environment and permanent CI job need separate evidence.
Morphology's current unit tests do not establish live Pymorphy dictionary
integration. Full hosted Ubuntu execution also remains unverified. Q7 remains
in progress; wiring all 103 modules does not resolve those outstanding checks.

F-Droid preparation deletes the four exact host CI gzip archives, verified by
hash and declared provenance; it does not add a blanket scanner exclusion.
Run host tests before preparation. See [F-Droid process](FDROID.md).

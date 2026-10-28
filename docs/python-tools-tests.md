# Python tools test inventory

Q7's tracked test scope is defined in `tools/ci/python_tools_tests.py`: all
`test_*.py` modules directly under `tools/typing_experiments` and
`tools/morphology`, plus `tools/test_qualification_artifacts.py`.
`tools/ci/python-tools-tests.json` assigns every tracked module exactly once.
Adding, removing or renaming a tracked module without updating this inventory
fails validation. Untracked local experiments are not CI inputs.

```sh
python tools/ci/python_tools_tests.py --check
python -m unittest discover -s tools/ci -p test_python_tools_tests.py -v
python tools/ci/python_tools_tests.py --profile stdlib --output build/python-tools-stdlib
python -m pip install -r tools/typing_experiments/requirements.txt
python tools/ci/historical_data_fixtures.py --install-build build
python tools/ci/python_tools_tests.py --profile scientific --output build/python-tools-scientific
```

Use Python 3.12 and a new output directory. Each test module runs in a separate
interpreter so generic imports such as `evaluate` and `train` cannot leak across
modules. PYTHONPATH and PYTHONHOME overrides are removed. Raw stdout/stderr,
child exit status, test counts and skipped tests remain in the output directory.
A failure or 240-second module timeout fails the profile; subsequent modules
still run. An empty suite fails. Existing output directories are never reused.
The workflow uploads both profiles' receipts and logs, including on failure.

Current scope: 92 stdlib modules, eight scientific modules using the existing
pinned NumPy/CatBoost requirements, and three historical-artifact modules. CI runs
the first two profiles in separate jobs. The scientific profile retains the
existing MLX-only test as a reported skip on Ubuntu; MLX gradient parity needs
its supported Apple environment. Installing CatBoost is not proof of frozen
model parity. Morphology's stdlib unit tests do not prove live Pymorphy dictionary
integration.

## Remaining historical gap

The scientific job first verifies and restores the original refinement and
additional-epoch public datasets from `tools/ci/historical-data-v1`. The two
original manifests and all 15 advertised files are preserved byte for byte.
The archive is about 1.85 MB, includes article attribution, and is checked
against the public source lock, original generator hashes and durable exclusions.
Installation requires fresh dataset directories and preserves other build files.
The additional-epoch 230-article/1,500-context exposure is now permanently
registered. Canonical-family and full-source-sentence recovery remains open.
See [the acceptance receipt](acceptance/2026-10-28-q7-historical-data.md) and the archive's NOTICE.

Q7 is **incomplete**. The following modules are inventoried but have no runnable
fresh-checkout CI job yet. They retain their original assertions; no replacement
models or synthetic datasets have been substituted:

| Module | Original artifacts needed under build/ |
| --- | --- |
| test_models.py | morphology-public-export-v3 receipt/data; typing-experiments CatBoost reference and neural parity cases |
| test_refinement.py | verified-observations and selected pairwise reference/export |
| test_word_ranking_data.py | typing-word-ranking/data manifest and rows |

Original candidate exports and model references have been located in the
nested historical workspace archive. They are not yet available in a fresh
checkout: receipts contain absolute paths and bind historical generator bytes.
Recovery must preserve those identities and establish a portable, verified
source/data/model bundle before wiring the `historical-artifacts` profile into
CI. Running that profile now fails rather than skipping absent
files. Updating the inventory cannot turn unresolved history into full coverage.
Live CatBoost/Pymorphy integration, MLX parity and hosted Ubuntu execution also
remain separate required evidence. See the review completion plan.

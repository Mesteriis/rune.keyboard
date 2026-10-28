# Q7: real morphology candidate exporter repair

Review's proposed change 4 is now checked against actual compiler/runtime output,
then integrated with its original two-file patch unchanged. The exporter must
compile the production correction/lexicon sources together with their pure
Kotlin experiment-policy dependencies; it excludes the Android resource loader
and worker. No shipped policy or asset is changed.

## Reproduction

A tracked-clean local checkout at `f9fcda4babc17ce397382a47c3fab3f46f9fbae7`
ran the original `evaluate.py export` command with Python 3.12.14, JDK17,
the existing pinned Kotlin compiler jars and installed Android 37.0 compile
stub. It failed with exit 1 and 60 compiler errors, including unresolved
`experiments`, `ContextualCorrectionPolicy` and `FrozenContextualAssets`.
It produced no successful export receipt.

Applying only the reviewed `evaluate.py`/`test_evaluate.py` bytes to that checkout
made the same full export pass: 4,000 existing RU rows (2,000 calibration and
2,000 holdout). The complete command took about eight seconds on this local Mac;
this is neither CI timing nor Android latency. All 21 selected experiment
sources compile without the Android resource loader or candidate worker.

A second separately compiled export in a fresh JVM matched all observations
after excluding only top-level `generationMs` and `baselineMs`. Every token,
candidate, search certificate and baseline decision is otherwise retained in
the comparison. Independent reconstruction of all 4,000 input envelopes proves
that only ordinal index and base64 token reach Kotlin; labels/context stay on
the Python side. Altering the raw observation file invalidates the original
receipt; restoring its bytes makes verification pass again.

All 63 morphology tests pass in the existing hash-locked Python 3.12 environment.
The exhaustive Python inventory still assigns 103 modules to runnable profiles.
CI now executes the full candidate export after Gradle/product replay and
uploads its compiler/generator logs and receipt. YAML structure and step order
were checked locally; the hosted workflow has not run.

The [machine receipt](2026-10-28-q7-morphology-export-evidence.json) binds the
original failure, both successful exports, semantic projection, 92 repository
source/asset inputs, changed files and private raw logs. All original owner's
13 payload hashes and 98 paths are preserved. The two reviewed files are now
tracked without altering their preserved bytes.

This repeats an already disclosed historical corpus. It is not a new holdout,
training epoch, policy promotion, Android editor test or device installation.
Q7 still requires actual hosted workflow execution; the broader review remains
in progress.

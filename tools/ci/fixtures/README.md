# Bounded word-ranking capture

`word-ranking-bounded-capture.json` is a disclosed regression fixture, not a
new holdout or an original-training reproduction. Four rows are selected from
the original word-ranking test, one for each declared error count 0–3. The first
100 characters of one original test text are retained for numerical execution.
The original full corpus/data manifest and per-article attribution are retained
by `historical_data_fixtures.py` / `historical_model_fixtures.py`; those archives
are verified before the surrounding smoke runs. Existing permanent article and
target-context exclusions apply. No private messages are included.

Source: Wikimedia Wikipedia, snapshot `20231101`, revision
`a634f78b1c435397c07001e175fa74cc4ad5e775`; Wikipedia contributors are the
original authors. Text metadata declares CC-BY-SA-3.0 and GFDL-1.3. The source
lock is `tools/model/rune-text-0.2/source-lock.json`; packaged license/attribution
is in `app/src/main/assets/smarttyping/experiments/NOTICE.md`.
Changes: selection of four existing synthetic spelling/control rows, truncation
of one text, and current JVM candidate generation. These rows were already
consumed/disclosed; no unseen-family/article or performance claim is made.

The four observations are actual `tools/morphology/evaluate.py export` output.
`originalExportFiles` preserves exact raw row/observation file hashes;
`sourceFiles` preserves 84 project source/asset identities from that export.
Compiler/runtime paths and raw host commands are deliberately excluded from the
portable fixture; the private local export receipt retains that evidence.

The smoke copies the hash-checked project inputs to a separate snapshot and
creates an explicitly marked portable derivative receipt. It binds all inputs
used by the maintained comparison, verifies denominators including absent
candidates, mutates every captured file and rejects second disclosure. It uses
identical published before/after weights and fixture-only selection metadata.
It does not reproduce original word-ranking or additional-epoch training,
selection, test candidate exports or model improvement. Refresh this capture
with a real exporter when its bound project sources intentionally change.


## Manual retrieval capture

`retrieval-bounded-capture.json` uses the exact four rows of the word fixture
above (bound by its SHA-256), with actual current baseline/manual-pool JVM
observations. It inherits the same original public text source, per-article
attribution, licenses and permanent exclusions. It retains project-source
identities and exact original raw row/observation hashes; runtime/compiler
paths remain in the private local export receipt. A portable derivative receipt
is explicitly marked as a fixture. It does not execute a fabricated compiler
or claim original historical retrieval reproduction.

The numerical driver preserves all three typo rows, including absent gold
candidates, and the separate correct control; it checks drift during actual
scoring and exclusive report writes. The separate `retrieval_export_smoke.py`
compiles and runs the actual observer on CI's real JDK/SDK, preserving its real
compiler/runtime file identities and logs. Neither driver grants independent
quality, production promotion or Android performance qualification.


## Joint controller rows

`joint-editor-disclosed-rows.json` retains four exact original rows from the
2026-10-25 joint holdout, one per short/long and typo/control combination. At
capture, every row was compared with the complete original holdout and both
manifest/holdout hashes were verified. Those hashes remain permanently bound
in the Q6 lexical ledger; CI checks that disclosure and the article history URLs.
CI does not reconstruct original row membership from the large public shards.
Historical numeric `family` labels are preserved without a new canonical-lemma
or unseen-family claim. The fixture is a regression input, never a holdout.

Source: Wikipedia contributors, Wikimedia `20231101` Russian snapshot, pinned
revision `a634f78b1c435397c07001e175fa74cc4ad5e775`, CC-BY-SA-3.0 / GFDL-1.3.
Per-article author attribution is linked through each `articleAttribution` history
URL; original shard hashes and manifest identities are retained. Changes are
selection of four existing synthetic typo/control rows and JSON packaging.
No personal messages or new text source is added; existing permanent joint
article/context/family exclusions apply, subject to their recorded gaps.

The native smoke performs fresh baseline/product runs on current source and
packaged models. Its policy record copies packaged thresholds and is explicitly
fixture-only; it does not recreate original training or checkpoint selection.
Raw Kotlin output uses opaque IDs, while a separate host map restores original
IDs for evaluation. Actual editor flags identify one old context deviation and
an existing baseline capitalization. Historical qualification remains false.


## Joint calibration rows

`joint-calibration-disclosed-rows.json` contains six exact original 2026-10-25
joint calibration rows: two short, two long acquisition and two long retention
examples selected using existing calibration scores. Exact membership and the
complete original manifest/calibration hashes were checked locally. CI checks
those permanently consumed ledger bindings and per-article author history URLs;
it does not reconstruct the full corpus from large public shards.

Attribution and licenses are the same pinned Russian Wikipedia snapshot/revision
and CC-BY-SA-3.0 / GFDL-1.3 terms described above. Each history URL identifies its
article's contributors. Changes are row selection and JSON packaging. Historical
family labels are preserved without asserting new canonical-family independence.
All rows were already consumed; no new private/natural holdout is introduced.

The native calibration smoke freshly exports these six inputs, copies published
weights and recomputes scores. Source/follow-up intentionally share this controlled
calibration corpus; this does not reproduce original independent follow-up data.
Four already disclosed editor-fixture rows provide a held-file hash; the recipes
never parse their labels. A deliberately invalid old-cache probe proves the
maintained source driver recomputes scores. No dummy compiler/JAR, model scores
or generator execution are substituted for the native/numerical run.

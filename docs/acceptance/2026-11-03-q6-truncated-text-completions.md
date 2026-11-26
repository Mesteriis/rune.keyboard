# Q6 source completions behind truncated historical text

The retained word-ranking, refinement and additional-epoch text archives contain
24 fragments cut inside a Russian word: respectively 4, 17 and 3. Against the
exact pinned Wikipedia shard, each fragment was matched to its article and word
ordinal; the complete original source token and context were retained. These
full source words extend beyond what the cleaned fragment actually contained and
are conservatively excluded, not asserted to have been consumed in full.

The 24 occurrences have 24 distinct full forms in 24 articles. Five forms were
already blocked by the control ledger; 19 are new. Dictionary-only analysis
of the completed heads produced 24 distinct family keys, 23 already present and
one new. Four heads remain unrecognized and are registered only as exact
unsupported surfaces; no lemma is guessed. The new registry entries cover 24
control contexts, 24 source contexts, the complete forms and articles, all known
families and four unsupported surfaces. All previous 53 control and 202 lexical
entries and their incomplete-coverage declarations are preserved.

Both public archives, the source shard, dictionary, pre-registration ledgers and
helper code are hash-bound and checked for drift. The two audit outputs and two
registry generations were byte-identical. The retained fixture hashes are
`dcb12d229bcaab7e9f12eb379a45d8e2f5cd4fc50e64bd48ceea14d6b344012e`
(contexts) and
`85dd773914d1afc6db92866f5854083c7cb83e44f25fe56da453acf0588fbee3`
(receipt). Reproducing the new-versus-existing counts requires the exact prior
ledgers. The registry verifies both archives, fragment ordinals and token
relationships; the original source audit binds the complete article bytes.
Historical provenance, unrecognized word families and independent qualification
remain open. No model, application or APK was changed.

The first registration attempt correctly rejected a proposed combined
context/family lexical entry (`LEDGER_SUPERVISED_FAMILY_SCOPE`); the final
registration stores those axes in separate schema-valid entries. Three audit
unit tests and three registration tests passed, including real surface/family
overlap and source/helper mutation checks. The final registration passed from a
staged source archive without `build/`; the existing isolated historical text
and named-regression checks passed on the expanded ledgers.

The 169-module standard-library run executed 821 tests with one failure and no
errors or skips: the pre-existing public-ledger test assumed exactly 13
unsupported-surface entries. The test was updated to assert this new family
entry explicitly (24 family keys and four unknown surfaces), while retaining all
prior 13-entry checks. The entire affected public-ledger module then passed all
24 tests. The full 169-module suite was not rerun after this test-only update;
its initial failure is retained under `build/q6-truncated-final-stdlib-20261103/`.
The test inventory check passed. Hosted CI and the scientific profile were not
rerun for this data slice.

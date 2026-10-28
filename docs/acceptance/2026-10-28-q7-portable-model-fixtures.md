# Q6/Q7: all historical Python modules run from versioned fixtures

All 103 tracked modules in Q7's tools scope are now assigned to runnable CI
profiles: 92 stdlib and 11 scientific modules. The historical-artifacts profile
is empty, and the runner's inventory test requires it to remain empty.

The three original artifact-dependent modules now enter explicit class-scoped
fixture workspaces. AST comparison confirms that all ten original test-method
bodies are unchanged. Production validators, expected counts, split checks,
corruption refusals and numeric tolerances were not modified. No historical
assertion was removed or replaced by a skip or tiny generated model.

## Fixture identity and relocation

The 4,643,389-byte archive contains 31 files / 46,842,719 payload bytes:
21 raw reference/data files and ten metadata path templates. Both full original
CBMs, decoded pairwise weights, parity cases, rows and observations retain their
original bytes and recorded SHA-256. The CBMs' upstream CatBoost build metadata
is retained; no model is reserialized. Generation verified both original export
receipts and all advertised files, and checked the 4,000 baseline rows against
already-versioned public spelling/protected-token data.

Only receipts, source-freeze maps and logs replace project/external paths with
explicit tokens. Runtime workspaces rebase the tokens and recompute metadata
hash edges. Data/source/model identities remain fixed. Baseline/refinement
profiles materialize the appropriate historical source snapshot; word-data tests
use the original data-manifest bindings. Unused runtime/export references are
metadata, not invented files or evidence of candidate-generation execution.
No archived script is executed. Temporary files and mocked resource roots are
removed/restored after each class.

Two independent archive generations matched all four package files byte for
byte. All 4,920 word-corpus articles have title/history attribution. Original
Wikipedia source terms and transformations are disclosed in the package NOTICE;
core refinement/additional-epoch attribution remains in historical-data-v1.
Original local build/parquet files are needed only for archive regeneration,
not ordinary CI execution.

All 9,000 word rows now have permanent target-context exclusions: 8,991 distinct
normalized keys (nine normalization collisions). The previous 125 ledger entries
are preserved; the context-only child supplements the original article entry.
The word-related pending statement now reflects that context recovery is done.
Canonical families/full source sentences and global Q6 completeness remain open.

## Actual checks

- Clean tracked checkout at source base 211e32c with only the bound candidate
  overlay, Python 3.12.14, no owner-local experiment files or original-build
  fallback: 92 stdlib modules / 518 tests pass; 11 scientific modules / 44 tests
  contain 43 passes and one existing MLX platform skip. All three restored
  modules pass their original ten tests, including full reference-tree parity,
  prior data/split identities and tampered-observation refusal.
- All 35 CI infrastructure tests, ten F-Droid data-policy tests and 15
  prepared-source tests pass. New fixture coverage includes fixed archive/model
  identity, failed outer-manifest rehash bypass, repository-path scope, metadata
  hash rebasing, temporary-copy isolation/cleanup, context exclusion and
  deterministic registration preserving prior records.
- The existing versioned original numeric-parity command still passes all
  8,555 vectors after the historical test module imports changed.
- Original owner's 13 payload hashes and 98 paths are preserved. No push,
  hosted workflow, device operation, new model training or APK update occurred.

## F-Droid integration

fdroidserver 2.4.5 flags gzip archives. The exact review data policy now has
29 entries: the original 24, four host archive deletions and one inventory-only
entry for the existing warning-only calibration gzip. Host archive deletions
bind their exact paths, bytes, SHA-256 and the matching manifest; no broad
scanignore or directory exception is added. The prepared-source policy binds
all four additional deletions (11 exact transformations total). Historical
versioned release recipes remain unchanged; a new recipe still needs its own
release/distribution acceptance.

The actual scanner ran offline on disposable source-base/submodule snapshots
plus the recorded candidate overlay. The original working checkout was not
scanned or deleted. Results:

| Scenario | Native fatal | Exact policy | Combined result |
| --- | ---: | --- | --- |
| Current overlay and exact deletions | 0 | PASS | PASS / exit 0 |
| Remove four host deletions | 4 | PASS | FAIL / exit 1 |
| Add real packaged ELF as archive-name prefix sibling | 0 | SCANNER_PREFIX_COLLISION | FAIL / exit 1 |

Two original warning-only findings remain (calibration gzip and upstream
Keynote). The ELF case demonstrates why native scanner prefix matching alone
cannot establish exact-file scope. This is a source scan, not an independent
F-Droid build-server or whole-release acceptance result.

Q7 remains in progress: supported MLX execution/CI, live Pymorphy integration and
full hosted Ubuntu workflow evidence are outstanding. This slice closes the
three formerly unwired module/resource gaps, not the whole review.

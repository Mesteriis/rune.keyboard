# Weighted candidate development qualification

This package preserves the independently reviewed **historical host result: 775/775 request contracts passed, but only 72/716 development retrieval requests completed under the unchanged 8,192-state /64-verification caps**. All 644 incomplete requests retain the AutoReplace veto. It does not turn coincidental top-seven equality into completion, select a new search algorithm, claim correction accuracy, or establish Android/physical-device performance or energy use.

There are 720 frozen development inputs and55 predeclared public controls. Four development inputs are valid words in another actual route and correctly veto retrieval. The independent full source oracle has 22,034 candidate records, including full neighborhoods for 440 missing routed pairs (EN 187, ES 251, RU 2). No holdout or calibration data is included or read. Original input, expected and raw-result identities remain unchanged.

## Historical evidence versus a new run

`evidence/original-manifest.json` is the exact 43-artifact manifest, SHA `45c2c6c91e69ccb78c042318d481c04b1a16589f0d41ae3f06057fc325648170`. Its 41 UTF-8 artifacts are preserved byte-for-byte in deterministic gzip/base64 text storage. The two original compiled binaries (`qualification.jar`, `unit_oracle`) are deliberately absent: their original sizes/hashes remain in that immutable manifest. No executable binary is embedded, downloaded or restored. The package reader pins the original manifest and compressed archive independently of mutable storage metadata, bounds decompression and verifies every decoded text record.

The archive includes the original scripts, README/report, input/expected/oracle files, numeric actual/per-query results, logs and source/compiler identities. Those original scripts retain their historical paths **as evidence**; they are not the promoted command interface. `evidence/original-report.md`, `original-review.md` and `summary.json` are readable copies. The original report discloses provenance-only assertion additions after its single production run. Promotion does not rerun or relabel that run.

The active `source/reference.py`, `QualificationMain.kt` and `unit_oracle.cpp` are byte-identical to the approved versions. The analyzer only receives its build path as an argument. Oracle reproduction has explicit source/manifest/compiler paths and optional reuse of pinned full-neighborhood records; weighted derivation logic is preserved. `test_contracts.py` checks these source/AST preservation boundaries as well as archive, numeric protocol, path and command admission.

Historical verification is read-only and executes no generator, compiler, oracle, Gradle or ADB:

```sh
python3 tools/lexicon/smart-typing-0.3/weighted-qualification/qualify.py verify-history
```

The success marker is `HISTORICAL_IDENTITY_PASS ... FRESH_EXECUTION 0`. It confirms saved evidence integrity; it is not a new 775-request result. To inspect all 41 original text artifacts in a new ignored directory:

```sh
python3 tools/lexicon/smart-typing-0.3/weighted-qualification/qualify.py --repo-root . export-history \
  --build-dir build/smart-typing-0.3/weighted-history-inspection
```

That export is explicitly marked historical and cannot be used as a prepared fresh-run directory.

## Portable fresh-run interface

Use Python 3.10+ without `-O`, a repository checkout matching the 13 production-source hashes in `manifests/historical-sources.json`, JDK 17 and the explicitly selected existing Gradle dependency cache. The reproduction toolchain pins Kotlin 2.2.10 and five cached jar identities. Only the compiler jar's historical hash was originally recorded; the other jar hashes constrain **new reproduction**, without claiming they were recorded during the historical run. No tool/dependency download or automatic source checkout occurs. Source drift fails closed; this package is not an unreviewed current-HEAD comparison against a silently changed baseline.

All data/build arguments are explicit paths relative to `--repo-root`; source output/index/rank directories must already exist inside that repository. Only a fresh descendant of its `build/` may be written, with no overlap with selected data inputs. Pre-existing symlinks anywhere in the output tree, including output leaves, fail closed. Read inputs are never mutated. The root of `--source-build-dir` contains `outputs/{en,es,ru}.words.txt` and `outputs/frequency/*.tsv`. `--index-dir` contains the six flat `*.trie`/`*.trie.lengths` files; `--rank-dir` contains the three flat `*.ranks` files. Existing source/packed-asset tools produce these artifacts; this package never expands dictionaries or builds indexes.

Example using explicitly selected verified caches (replace paths with your repository-relative build directories):

```sh
python3 tools/lexicon/smart-typing-0.3/weighted-qualification/qualify.py --repo-root . prepare \
  --build-dir build/smart-typing-0.3/weighted-run-01 \
  --source-build-dir build/smart-typing-0.3/lexicon-prototype \
  --index-dir build/smart-typing-0.3/lexicon-index-prototype/assets \
  --rank-dir build/smart-typing-0.3/packed-lexicon-reader-prototype/rank-assets
```

Those example directories are optional cache choices, not hidden dependencies. Any directory with the same pinned artifacts and documented layout works. The original ignored qualification package is never consulted. Before writes, preparation verifies the source keys/frequencies, all nine packed files and historical production-source identities. It materializes frozen fixtures/oracle data only, and records relative input paths and hashes in `qualification-owner.json`. It imports no actual run, compiled binary or success log.

Optional expected-data reproduction must precede execution. By default it independently rereads canonical sources for membership/ranks/ordinals and regenerates all weighted/case/route/dedup expectations using the pinned complete neighborhood records. It does not claim to repeat the prior full scans:

```sh
python3 tools/lexicon/smart-typing-0.3/weighted-qualification/qualify.py --repo-root . derive-oracle \
  --build-dir build/smart-typing-0.3/weighted-run-01
```

To explicitly recompile the unchanged independent C++ oracle and repeat only the 440 missing-route full scans, use a **separate fresh prepared build directory**, then `derive-oracle --build-dir ... --rescan-missing --cxx clang++`. The C++ child limit is 60 seconds for compilation and 900 seconds per language scan. The matching-language complete neighborhoods continue to use the frozen inherited oracle; no benchmark timings are generated. Every regenerated fixture/neighborhood must equal the pinned historical bytes before production execution is allowed.

Compile and execute are separate explicit operations:

```sh
python3 tools/lexicon/smart-typing-0.3/weighted-qualification/qualify.py --repo-root . compile \
  --build-dir build/smart-typing-0.3/weighted-run-01 \
  --java java --gradle-cache "$HOME/.gradle/caches/modules-2/files-2.1"
python3 tools/lexicon/smart-typing-0.3/weighted-qualification/qualify.py --repo-root . run \
  --build-dir build/smart-typing-0.3/weighted-run-01 \
  --java java --gradle-cache "$HOME/.gradle/caches/modules-2/files-2.1"
python3 tools/lexicon/smart-typing-0.3/weighted-qualification/qualify.py --repo-root . compare \
  --build-dir build/smart-typing-0.3/weighted-run-01
```

`--java` resolves the caller's JDK 17 command (or explicit executable path); there is no Homebrew/Linux-specific default. Compilation uses two active processors, 768MiB heap and 120-second timeout. Execution uses the same worker limits and 300-second timeout. The actual public Kotlin harness and reader fully validate the mapped assets, then run exactly 775 requests. Numeric record schema is unchanged. No text/path/PID/device identifiers are added to result rows; captured child errors become static public failures. A failed or partially written stage never receives a success identity and cannot be silently resumed over old output; choose a fresh build directory.

`reports/run.json` initially has `comparison_passed:false`. `compare` validates numeric envelopes and the unchanged semantic analyzer; only a successful comparison sets it true. Complete results must contain the full independent routed terminal set and exact weighted final selection; incomplete results must be verified subsets with the strict veto. All states/verifications share the existing cross-route budget. Source hashes are checked around execution. A new run has its own artifact/actual hashes; it is never appended to historical evidence.

**Promotion validation did not run these compile/run/derive-oracle commands.** It checked command/parser/provenance behavior and real existing cache identities only. No new retrieval, C++ scan, model, device, performance or holdout result is implied by this README.

## Interface regression checks

```sh
RUNE_QUAL_TEST_DIR="$PWD/build/smart-typing-0.3/weighted-contracts" \
  python3 tools/lexicon/smart-typing-0.3/weighted-qualification/test_contracts.py
```

The explicit directory holds only temporary interface fixtures. Tests verify the archive identities, immutable manifest replacement rejection, numeric parser limits/ownership/veto, relative build confinement, leaf/directory symlink rejection, required tool/data arguments, source semantic preservation and a **mocked** runner path/timeout/non-overwrite contract. They neither execute the generator nor compile/run the C++ oracle. Original full-reference/Dijkstra and negative semantic logs remain historical evidence in the archive, rather than being counted again.

See `DATA-NOTICES.md` for source boundaries and `../../../../docs/acceptance/2026-09-02-smart-typing-0.3-weighted-development-qualification.md` via repository navigation for the acceptance limits. No new AutoReplace or search-feasibility gate is closed by packaging this evidence.

# Q1: current F-Droid source scanner and source checkpoint

On committed source `f3e98a7b`, the local release source check initially
returned `RELEASE_SUBMODULE_NOT_READY`: the existing llama.cpp checkout was
clean and already at the pinned revision, but the parent Git configuration
had not registered it. `git submodule init` registered that existing checkout
without changing its source or switching revisions. The ordinary release source
check then passed with zero status entries and one matching submodule. This is
local Git configuration, not a repository or release change.

The current F-Droid data policy passed with 31 entries, 19 exact scanignore
paths and five scandelete paths; its 12 unit tests passed. The actual
fdroidserver 2.4.5 source scanner then ran on a separate clean clone with the
pinned submodule, the current reviewed overlay and network disabled. The
unmodified packaged SUSS defaults supplied 585 error signatures; their SHA-256
was `c262fb68063777dad15ff701b07bbb1b3a9c9e19aa623a0ddea524ff0a5c3a33`.
The scanner reported zero fatal findings and two warnings: the calibration
`tsv.gz` test fixture and llama.cpp's `idea-arch.key` documentation file.
These match the previously reported warning categories.

Two separate disposable negative clones used an existing packaged ARM64 ELF as
an injected test file. An unreviewed `.bin` caused one native scanner fatal and
`UNREVIEWED_OR_STALE_DATA_SET` in the additional data guard. A sibling named
`ru-ranker.bin.injected.so` demonstrated the native scanner's prefix-exception
behavior (zero scanner fatals), while the guard correctly rejected it with
`SCANNER_PREFIX_COLLISION`. The original signed APK was only read as a source
of test bytes. All temporary clones, injected files and the scanner environment
were removed.

This is a local source scan using the packaged default signatures, not the
current signatures of an F-Droid build server. It does not verify a new release
recipe, a final APK or independent build-server reproducibility; those remain
open, along with the separate Q6 provenance and qualification requirements.

## Repeat after corpus-exclusion updates

At clean source `999bb3213083b655a756c6df8733fbbb5c7986b1`, the exact data
policy again passed with 31 entries, 19 scanignore and five scandelete paths;
its 12 unit tests passed. F-Droid 2.4.5 scanned a separate clean temporary
checkout with the pinned submodule and network disabled in the scanner. It
used the packaged SUSS defaults (585 error signatures; SHA-256
`c262fb68063777dad15ff701b07bbb1b3a9c9e19aa623a0ddea524ff0a5c3a33`)
and reported zero fatal findings and the same two warnings: the calibration
`tsv.gz` and `idea-arch.key` documentation file.

The temporary scanner environment and checkout were removed. Actual command
logs and exit codes are retained under `build/ci-editing-investigation/q1-post-corpus`.
This remains a local scanner result, not current build-server signatures,
independent build-server acceptance or distribution.

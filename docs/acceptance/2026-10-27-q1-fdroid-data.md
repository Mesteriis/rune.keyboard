# Q1 — exact current-data overlay and native scanner checks

fdroid/review-data-policy.json inventories 24 fixed files at source basis 4278bca:
13 shipped .bin/.ctx/.gram assets, nine numeric test .bin/.gram fixtures, the
Unicode/CLDR source-data ZIP and the existing non-shipped training baseline.
Each has byte size/SHA-256 and a hash-bound declared provenance JSON reference.
These references are evidence bindings, not a new finding of authorship or license
completeness; the independent Q6 audit remains open.

The review overlay emits 19 literal scanignore names (ten shipped .bin files,
eight numeric test .bin fixtures and one source-data ZIP), four inventory-only
index paths and one exact scandelete baseline path. The four indexes are not
scanner errors under fdroidserver 2.4.5; adding unused exclusions would fail that
scanner. No directory/glob exclusion is introduced. Existing historical recipes
retain exceptions applicable to their original source commits. The overlay is
for a future versioned recipe; it does not reassign historical 0.4.2 to HEAD.

The standard-library validator checks current data against the fixed inventory,
content hashes and declared provenance hashes. It rejects changed/extra/missing
files, symlinks, unsafe/private provenance paths, incorrect suppression actions
and duplicate keys/entries. Its prefix guard matters because upstream 2.4.5 uses
startswith after resolving even literal file exceptions. Unexpected sibling files
or directories must not inherit a reviewed file's suppression. CI runs the data
validator and its seven regression cases before the existing corpus checks; this
is not an automatic full F-Droid source scan or remote CI result.

The actual fdroidserver 2.4.5 scanner ran on disposable copies of immutable git
snapshot 4278bca plus its own pinned llama.cpp submodule. The original working
repository was not scanned because scanner preparation deletes wrappers and
scandelete targets. The overlay was validated before scanning and applied to the
Build object's literal scanignore/scandelete lists. The source commit/profile
identities were bound explicitly. No distribution build was executed.

| Scenario | Native scanner fatal | Data guard | Combined outcome |
| --- | ---: | --- | --- |
| Reviewed snapshot with overlay | 0 | PASS | PASS / exit 0 |
| Add an unrelated prebuilt native library as unreviewed.bin | 1 | UNREVIEWED_OR_STALE_DATA_SET | FAIL / exit 1 |
| Add that library as ru-ranker.bin.injected.so | 0 | SCANNER_PREFIX_COLLISION | FAIL / exit 1 |

Both negative files used actual packaged arm64 librune_llama bytes in temporary
copies. The second case explicitly demonstrates why the native scanner alone
cannot prove exact-file suppression scope. The overlay's known files were not
broadened to make either case pass. Each scan keeps the two historical warnings:
calibration.tsv.gz and the upstream Keynote document. Package SUSS defaults were
unmodified and hash-bound with a nonempty Gradle signature set; network socket
creation was blocked during scans. This does not represent current build-server
signature data. Temporary source copies were removed.

Seven standard-library regression tests pass. The working-copy data policy check
passes against all 24 byte/provenance identities, and the original offline emoji
catalog generator check passes (1,898 entries). No APK/runtime/scoring source or
asset changed, no fresh typing replay was run, no phone used/updated and no
release/tag pushed. No isolated F-Droid build-server acceptance is claimed.

Q1 still needs a next versioned distribution recipe, clean-source release
requirements and applicable release/model/device evidence. U16's strict source-
path audit and Q6's unresolved provenance are not closed by this overlay.

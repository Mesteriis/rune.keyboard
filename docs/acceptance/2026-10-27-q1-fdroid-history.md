# Q1 — historical F-Droid source identity restored

The original 0.4.2 preparation commit is d332c0e, with versionName 0.4.2,
versionCode 8, matching CHANGELOG, store changelogs and the existing build recipe.
Before this step v0.4.2 was absent locally and an explicit remote tag read returned
no matching refs. An annotated local v0.4.2 now points to that historical commit.
No tag was forced, pushed or used to publish a new release. Current review HEAD
has later changes and is not the historical version's source.

The two existing F-Droid entries now use the complete commits resolved from
v0.4.1/v0.4.2, preserving their actual source identities. Their historical three
scanignore paths and one scandelete path remain unchanged. The current-source
policy belongs to subsequent review work; adding absent new paths to historical
recipes would cause unused-scanignore failures in fdroidserver 2.4.5.

A private isolated fdroidserver 2.4.5 environment was installed for the real
validator/scanner. The official category catalogue and eleven required icons
were captured and hash-bound. Metadata lint returns exit 0. The first lint setup
attempt failed because the captured catalogue referenced icons not yet downloaded;
that failure is retained, then the required real icons were fetched and lint rerun.
No fake icons or category filtering was used.

Two immutable git archives (historical d332c0e and current review 0f24f2e), each
with its own recorded llama.cpp gitlink, were extracted into disposable copies.
The actual scanner ran there because it removes wrappers/scandelete files. The
working repository was not passed to scan_source. Package SUSS defaults were
unmodified, nonempty and hash-bound; socket creation was blocked during scanning.
This is a pinned offline scanner result, not a claim about future server signatures.

- Historical source: zero fatal findings, two warnings (calibration.tsv.gz and
  the upstream Keynote document).
- Current review source with historical exceptions: eight fatal findings (seven
  new numeric .bin assets and the Unicode/CLDR source ZIP), ten warnings (eight
  numeric test .bin fixtures plus the two historical warnings).
- Two initial private-harness attempts failed before completion because a generic
  YAML 1.1 parser converted unquoted yes to bool. The harness now uses the official
  F-Droid metadata parser. Those setup failures are not counted as source scans.

The adjacent evidence binds commits, tag object, archives, scanner/parser/signature
identities, official category inputs, actual results and setup failures. Local tag
creation and metadata lint do not establish remote tag publication, official
inclusion, isolated build-server success, current-source data acceptance or Q6
training/corpus provenance. Q1 remains open for those applicable release requirements.

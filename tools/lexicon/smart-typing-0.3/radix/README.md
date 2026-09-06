# Lossless radix index qualification

This is an offline experiment, not an APK format migration or a relaxed search
budget. The current production reader and exact top-seven selector are unchanged.

Calibration diagnosis at `bff8110a54c05984a34f8aac4b963e5b3c8e4d02` found most
EN state exhaustion at lengths 7–12. In the frozen EN trie, 130818 of 272385 nodes
are nonterminal nodes with exactly one child. A radix edge can encode each such
maximal path as one indexed record. RU/ES have 558058/509338 collapsible nodes.
This suggests a smaller state space; it does not yet prove better bounded
candidate retrieval or CPU performance.

## Format and preservation

RDX1 uses little-endian integers. Its 24-byte header is magic `RDX1`, version1,
node count, terminal count, record size20, UTF-8 label-blob bytes. Each record is:

| Field | Bytes |
| --- | ---: |
| Label offset in blob | 4 |
| First child index (zero means absent) | 4 |
| Next sibling index (zero means absent) | 4 |
| Original terminal ordinal (zero means nonterminal) | 4 |
| Label scalar count | 1 |
| Label UTF-8 byte count | 1 |
| Minimum descendant word scalar length | 1 |
| Maximum descendant word scalar length | 1 |

Root record0 has an empty label, no sibling/terminal, and the ordinary descendant
length bounds. Nonroot labels contain1–32 scalars and at most128 strict UTF-8
bytes. Records and label spans are contiguous in scalar-lexical preorder.
Terminals preserve their original ordinals, so the separate licensed frequency
rank component requires no reordering or regeneration. Compression never crosses
a terminal or branching node. The source's exact word stream SHA-256 and every
terminal ID are checked, including prefix words and supplementary scalars.

Input SHA-256 and sizes are checked against the pinned packed-asset manifest.
Derivation checks source structure/length bounds and emits a separate format.
An independent compressed-edge decoder then checks record topology, UTF-8,
depth, scalar sibling order, maximal compression, exact subtree lengths,
contiguous storage, terminal ordinal sequence and the full decoded word digest.
Neither phase normalizes, prunes or adds words. Frequency sources, corpus
labels and holdout are not read. Root/sibling/chain traversal uses at most32
scalar depths. Full artifacts remain under ignored `build/`; reports retain
their digests. Original orthographic notices and source attribution remain those
listed in `../packed-asset-manifest.json` and `../PACKAGED_LEXICONS.md`.

```sh
python3 -m unittest discover -s tools/lexicon/smart-typing-0.3/radix -p 'test_*.py'
python3 tools/lexicon/smart-typing-0.3/radix/derive.py \
  --index-dir build/smart-typing-0.3/lexicon-index-prototype/assets \
  --output build/smart-typing-0.3/radix-derivation-fresh
```

Next: implement and qualify an experimental radix reader/selector against the
unchanged full oracle, with the8192-record and64-verification caps shared across
membership and both languages. Processing every scalar within a compressed
edge must preserve unrestricted transpositions, inherited bounds, cancellation
and partial-expansion rules. Before production adoption, compare calibration
coverage, CPU, mapping/validation cost and APK/RAM on the same controls, then
integrate strict load/manifest validation. No results for those checks are
claimed by the converter alone.

## Search probe outcome

`probe.py` now builds a host-only RDX1 reader and a generated adaptation of the
pinned production selector. It verifies the source/harness SHA before changing
the edge traversal, retains the original exact-membership reader and ranks, and
uses the same full-corpus input protocol. Full paths use a fixed1MiB extra scratch
array, cleared after each request. This is not a production memory design.
Every scalar inside each compressed edge still runs through the unrestricted
recurrence, with cancellation checkpoints and inherited bounds. Certificate
checks remain outside the entire child-list expansion.

The probe passed the773-request oracle but regressed24 complete calibration rows
and gained22; EN complete-correct retrieval fell184→175. It is **not adopted**.
No Android performance or model/holdout qualification followed this failed
feasibility check. Source, generated overlays and evidence are preserved in
`results/2026-09-03-search-probe/`. The next product direction is the explicit
candidate-width evaluation in `../top-seven/`, not integrating this prototype.

Reproduce against the pinned selector/harness versions checked by the script:

```sh
python3 tools/lexicon/smart-typing-0.3/radix/probe.py \
  --output build/smart-typing-0.3/radix-probe-fresh \
  --index-dir build/smart-typing-0.3/lexicon-index-prototype/assets \
  --rank-dir build/smart-typing-0.3/packed-lexicon-reader-prototype/rank-assets \
  --radix-dir build/smart-typing-0.3/radix-derivation-fresh \
  --java java --gradle-cache "$HOME/.gradle/caches/modules-2/files-2.1"
```

Use the emitted `assets/` directory as `--rank-dir` and the probe output root as
`--compiled-export` for the existing full-width oracle verifier. The generated
identity class pins and checks all radix asset hashes on load. Original scalar
trie/rank hashes and every compiled source are also recorded and checked.

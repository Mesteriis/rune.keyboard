# PR6 offline lexicon inputs prototype

All work is confined to this ignored build directory. No tracked product/tool
files, Gradle tasks, APKs, model training, corpus/holdout changes or publications.
This is a frozen finite input dataset for a later runtime-index comparison,
not PR6 product qualification or a complete enumeration of Hunspell's language.

## Frozen datasets

| Component | Canonical lowercase NFC keys | Bytes | SHA-256 |
|---|---:|---:|---|
| RU | 1,436,553 | 33,008,833 | `b54c01203aad985845c7b79116e57b818fde5e647f66f735bddb0b3239249401` |
| EN | 121,255 | 1,173,857 | `67f5299ebd264abb62518b01dae9ea36837d39dfcfe76d731983841bc9794d26` |
| ES | 668,267 | 7,791,505 | `0a304ca9c3269498f82e573b44c9b80f4135e6e596ed947205cfa26b6f4530dd` |

Inputs for all three candidate runtime formats must be identical
`outputs/{ru,en,es}.words.txt` files, with these SHA-256 values verified first.
Original-case NFC surfaces remain in separate `*.surface-forms.txt` files:
RU 1,437,107; EN 123,679; ES 668,557. Their hashes are in `output-manifest.json`.
Case collisions collapse only in the canonical key file; surface forms preserve
the information needed to derive a key-to-case mapping. No source case is inferred.

Frequency data is separate: `outputs/frequency/{ru,en,es}.tsv`, 50,000 source
rows each, with original rank/count/word and an added normalized key. There are
zero normalized-key collisions in these pinned lists. These are CC-BY-SA assets,
not dictionary truth or a merged orthographic/frequency derivative.

## Exact finite RU/ES profile

- Maximum 32 Unicode codepoints. UTF-8, LF, unique codepoint sort; this agrees
  with unsigned UTF-8 byte order. NFC, then RU/EN/ES lowercase, then NFC.
  No NFKC, casefold, accent stripping, `ñ` deletion, or `ё` to `е` collapse.
- Parse actual source syntax only; unsupported directives fail closed. RU has
  SET/TRY/SFX: 25 ASCII flag classes and 1,581 suffix rules. ES has SET, FLAG
  UTF-8, TRY, MAP, REP, PFX and SFX: 6,742 lexical rules total. MAP/REP/TRY are
  explicitly suggestion-only, retained as source but do not create lexicon forms.
- Enumerate source roots, zero/one prefix, zero/one primary suffix, and at most
  one continuation suffix. Existing continuations are only `S` and `GS`, and
  their target rules have no further continuations. Prefix/suffix crossproducts
  respect Y/N flags; prefix order before, between, or after suffix steps is
  enumerated. Native spell acceptance rejects any surplus candidate.
- No speculative compound joining, implicit hyphen BREAK expansion, terminal-dot
  synthesis, or automatic capitalization variants. Explicit source forms remain.
- Native `HashMgr::decode_flag/decode_flags` provides all flag IDs. This matters:
  pinned Hunspell uses 16-bit flags; an astral flag becomes U+FFFD and truncates
  the remaining flag vector. Different astral flags can collide. The two-codepoint
  `☎️` header uses the first codepoint, while a dictionary vector contains both.
  This prototype matches **the pinned native semantics**, not a repaired Unicode
  interpretation. `reports/es-native-flags.tsv` preserves exact decoding. This
  source/tool compatibility limitation remains visible for later source selection.
- Dictionary whitespace is trimmed to lexical tokens. Only ES source line 92
  changes (`Araba ` to `Araba`); exact source bytes and the witness are retained.
- The native checker accepts every retained RU/ES surface before normalization.
  Lowercase keys of uppercase-only roots are lookup keys, not a claim that the
  lowercase spelling alone passes native Hunspell. Original case stays available.

## Measured validation and boundaries

Legacy pinned `unmunch` is rejected as the authoritative generator. RU loses
3,685 native-accepted public frequency-probe words; ES loses 424 and emits
2,633 forms containing literal continuation markers such as `/S|`.
The JSON and complete word witnesses are in `reports/unmunch-validation.json`
and `reports/*-unmunch-missing-known.tsv`.

Finite Unicode generation yields RU 1,437,107 candidates, all accepted. ES yields
668,561 candidates, of which four are rejected and excluded: `deshice`, `deshizo`,
`rehíce`, `rehízo`. Accepted legacy RU forms are a subset. ES has one accepted
legacy-only string, `Araba `, accounted for by the explicit whitespace policy.

Among native-accepted words in the separate 50k public frequency probes,
RU has 435 finite-profile omissions (395 hyphenated, 40 terminal-dot); ES has
143 (105 hyphenated, 38 terminal-dot). There are no other spelling-shape
categories. These categories do not prove a derivation for every omitted word;
all residue remains in `reports/*-finite-missing-known.txt`. This is not a
held-out quality score, and no quality corpus was read or tuned.

RU/ES generation was run twice: surface and key bytes match exactly. SCOWL was
built from the same archive in two fresh directories; both selected 123,679
ISO-8859-1 rows with SHA-256
`2d85306ee69f0b01925d703299efc67d4830aef72e990d816a0ab040d2fb55b2`.
SCOWL uses `en_US 60`, upstream default non-variants and `--accents keep`.
It preserves source accents (e.g. café, jalapeño, fiancée); it does not invent
accent variants absent from the selected source (e.g. naïve or résumé).

macOS build requirements were verified rather than hidden:

- GNU find is required for upstream `find -printf`.
- GNU grep is required for the BRE alternation in `scowl/src/filter`.
  System grep retained only `I/a` in a four-word witness; GNU grep retained all
  four. The failed BSD build's 1,777-row selection is not a canonical output.
- Upstream make is not parallel-safe; `-j2` raced on
  `working/possessive-also.lst`. Clean serial `make -j1`, with local PATH links
  to already installed GNU find/grep, produced the verified full output.
- `reports/toolchain.json` records compiler, Python/Unicode, make, Perl, native
  binary and utility versions/hashes; sources and build commands are retained.
  No global packages were installed. Host binaries are never APK dependencies.

## Reusable commands

Run from this prototype directory. `source-lock.json` holds immutable source
revisions plus observed first-acquisition hashes, and is the fail-closed lock for
subsequent acquisition. These are observed hashes, not upstream signed attestations.
For an existing frozen package, run `verify_outputs.py` first: it verifies the
manifest's frozen `source-lock.json` hash before any source loader can use its
URLs, revisions or reuse paths. Updating a URL or revision without matching the
frozen manifest is a verification failure, even when the input bytes are unchanged.

FrequencyWords reuse is an optional local cache. If it is absent, `--fetch`
downloads the exact locked URL and then verifies the locked SHA-256; without
`--fetch` the missing source fails closed. An existing cache is still hash-checked.
SCOWL Copyright is read directly from the SHA-256-verified pinned archive,
independently of any old `sources/wordlist-*` checkout or fresh build directory.

```sh
python3 scripts/fetch_sources.py                    # offline hash verification
python3 scripts/fetch_sources.py --fetch            # only if pinned inputs are missing
python3 scripts/build_host_tools.py --scowl-work rebuild-001
python3 scripts/check_unmunch.py
python3 scripts/expand_affixes.py > reports/finite-expansion.log
python3 scripts/expand_affixes.py > reports/finite-expansion-repeat.log
python3 scripts/finalize_inputs.py
python3 scripts/verify_outputs.py
python3 -m unittest discover -s scripts -p test_source_pipeline.py -v
```

Choose a fresh `--scowl-work` directory; the script refuses to reuse one. A full
rerun rebuilds only local host tools and work files. Compare the new selected
SCOWL bytes to `reports/en-scowl60-first-gnu-latin1.txt` before freezing a changed
source/output manifest; `reports/scowl-reproducibility.json` records this run's
two-clean-build comparison. Immutable output hashes above remain the current
benchmark inputs. Do not label new different data as this frozen dataset.

`THIRD_PARTY_NOTICES.md`, `notices/`, original inputs, archives, transformations,
`source-lock.json`, `reports/archive-members.json`, and `output-manifest.json`
are the redistribution/provenance package. RU notice stays permissive, ES stays
a separate MPL asset, and frequency stays separate CC-BY-SA 4.0. No runtime index,
APK-size claim, Android performance claim or lexical quality qualification is made.

## Source review corrections

The source acquisition/provenance review added seven regressions covering missing
reuse with and without network authorization, incorrect downloaded bytes, existing
offline cache, clean archive-only SCOWL notice extraction, tampered archive bytes,
and URL/revision/reuse-path changes in the frozen source lock. Network acquisition
is mocked in these tests. All seven pass. An additional extraction using the real
locked SCOWL archive in a temporary directory without `sources/` reproduced the
exact 11,758-byte Copyright notice, SHA-256
`283326a422e29c510e2ba6805518c418ce3c35ed1fadc3eec83d2da4f6c5a055`.

The nine frozen wordform/frequency files and the original source-lock hash remain
unchanged. Only the manifest's transformation-source records were refreshed for
the reviewed script edits and added regression file; no failing source/data hash
was accepted as a new baseline. Evidence is under `reports/source-fixes-*`.

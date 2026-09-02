# Frozen Smart Typing 0.3 lexicon source pipeline

This package reproduces the reviewed RU, EN and ES word-form inputs. It does not
choose a runtime index or package dictionaries, Hunspell or frequency data in an
APK. Every mutable input, host tool, work tree, diagnostic and generated word list
lives in an **explicit, dedicated project `build/` directory**.

## Immutable source and output contract

`source-lock.json` is preserved byte-for-byte at SHA-256
`28750e183ef99ea33da58b20036e2f0dcb3f7e1f76e8528c21074ac7d6615b70`.
The loader checks this hash before trusting any URL, revision or path. A missing
lock fails closed; there is no unpinned `source-inputs.json` bootstrap and no lock
regeneration. The historical `reuse` strings remain in the immutable JSON but
are not followed. Cache reuse is allowed only through explicit `--source-cache`.

| Language | Canonical word forms | Bytes | SHA-256 |
|---|---:|---:|---|
| RU | 1,436,553 | 33,008,833 | `b54c01203aad985845c7b79116e57b818fde5e647f66f735bddb0b3239249401` |
| EN | 121,255 | 1,173,857 | `67f5299ebd264abb62518b01dae9ea36837d39dfcfe76d731983841bc9794d26` |
| ES | 668,267 | 7,791,505 | `0a304ca9c3269498f82e573b44c9b80f4135e6e596ed947205cfa26b6f4530dd` |

`frozen-output-manifest.json` is the unchanged reviewed manifest. Its raw bytes
are pinned to SHA-256 `ec26c80edd28f2b42008a844c8b0ce83c11759386ccc9de591cb038a7a4f3c48`
by the shared loader before preparation or verification trusts its records. It also freezes
original-case surface forms (RU 1,437,107; EN 123,679; ES 668,557), three separate
50,000-row frequency components, source lock and original notices. Its old
transformation hashes document the reviewed prototype, not the promoted files.
New run provenance records current package scripts with `scope: "tool"`; output
identities are always checked against the unchanged frozen manifest. Different
outputs fail verification and are never silently accepted as a new baseline.

## Language, normalization and license boundaries

* **RU:** the pinned LibreOffice `ru_RU` dictionary has the separate permissive
  Alexander I. Lebedev terms. Preserve `notices/RU-Lebedev.txt` with derived data.
* **ES:** the separate Spanish dictionary component uses the upstream MPL 1.1
  option. Keep the original `.aff`/`.dic`, modification/transformation source and
  the MPL/attribution notices available with derived Spanish assets. It is not
  relicensed as application code.
* **EN:** SCOWL is a multi-source component. Preserve the entire
  `notices/SCOWL-Copyright.txt`, including WordNet and UKACD material; do not
  replace it with a shorthand MIT label.
* **FrequencyWords:** content is **CC-BY-SA 4.0**, separately from its repository's
  MIT code license. `outputs/frequency/*.tsv` retain original word, rank and count
  plus a normalized key. No frequency values are embedded in orthographic files.
* **Hunspell:** the pinned native checker and diagnostic `unmunch` are host tools
  only, never Android/runtime dependencies. Original alternative license texts
  are retained independently of the dictionary-data licenses.

See `THIRD_PARTY_NOTICES.md` and the verbatim original texts in `notices/`.
All pins and archive-member identities are retained. Hashes were observed during
reviewed acquisition; they are not upstream signed attestations.

Normalization is NFC → RU/EN/ES lowercase → NFC, UTF-8, LF, unique Unicode
codepoint order, maximum 32 codepoints. Preserve accents, `ñ`, and `ё`; do not
casefold, apply NFKC or collapse `ё` to `е`. Original-case surfaces stay separate.

RU/ES use the reviewed finite affix profile: source roots; at most one prefix;
one primary suffix and one allowed continuation suffix; native acceptance after
expansion. Unsupported lexical directives fail closed. Suggestion-only MAP/REP/
TRY do not generate word forms. There is no speculative compound/BREAK joining,
terminal-dot synthesis or invented capitalization. ES source line 92 (`Araba `)
is trimmed to its lexical token; generated diagnostics retain the witness.

Pinned Hunspell's actual 16-bit flag behavior is preserved, including astral
flag replacement/truncation and the two-codepoint `☎️` vector. This is not a
Unicode repair of upstream data. Four generated ES forms (`deshice`, `deshizo`,
`rehíce`, `rehízo`) are rejected by the native checker and excluded. The finite
profile omits 435 RU and 143 ES native-accepted public frequency probes, consisting
of hyphenated/terminal-dot shapes. These are visible scope limitations, not a
holdout quality result. The complete reviewed rationale and historical counts
are in `provenance/reviewed-source-profile.md`.

## Commands

Run from the repository root. Python 3.11 with tar extraction data filters,
C++17, GNU find, GNU grep, make, Perl and standard host utilities are required.
The reviewed host used Python 3.11.14. Tools are recorded, not installed. On
macOS the upstream SCOWL build needs GNU find/grep; BSD grep produced a rejected
1,777-row selection. SCOWL make must be serial (`-j1`) because its generated
possessive-list work files race under parallel make.

```sh
PIPELINE=tools/lexicon/smart-typing-0.3/pipeline.py

# Fast offline regression suite: no sources, network or native build required.
python3 "$PIPELINE" --build-dir build/lexicon-regression test

# Explicit reuse from a cache containing the locked sources/ and downloads/ paths.
python3 "$PIPELINE" --build-dir build/lexicon-run-001 --source-cache /path/to/reviewed-cache acquire

# Or explicitly authorize fetching only missing pinned inputs.
python3 "$PIPELINE" --build-dir build/lexicon-run-001 --fetch acquire

# Full cold/offline reproduction after acquisition, in a fresh work directory.
python3 "$PIPELINE" --build-dir build/lexicon-run-001 reproduce

# Subsequent verification of an already reproduced artifact set.
python3 "$PIPELINE" --build-dir build/lexicon-run-001 verify
```

A fresh cache-free run can combine acquisition and reproduction with explicit
`--fetch reproduce`. Without `--fetch`, missing data fails; existing corrupted
cache/target files fail even when fetching is allowed. Downloads are staged and
published only after exact SHA/size verification. There is no network access
from the tests except mocked acquisition. No old prototype path is required.

`reproduce` performs two fresh serial SCOWL builds, requires both to match the
frozen 123,679-row Latin-1 selection, runs the rejected-unmunch diagnostics, runs
finite RU/ES expansion twice, finalizes normalized/frequency/notices provenance,
and verifies the frozen identities. Existing SCOWL work directories are refused;
choose another dedicated build directory for another full run. Nothing installs
or changes global host tools.

Individual stages are `acquire`, `host` (with `--scowl-work NAME`), `diagnose`,
`expand` (both finite runs), `finalize`, and `verify`. Use `pipeline.py` as the
public entry point: it validates the build directory, immutable metadata and
source bytes before launching source-dependent stages. Files under `scripts/`
are internal workers using the wrapper's build context. A standalone `host`
stage is useful for diagnosis; only full `reproduce` establishes the two-build
SCOWL report needed by final verification.

Build directories must be physical children of project `build/`, cannot be the
build root itself, and cannot redirect through a build-root symlink. They receive
a local `.gitignore`. Package `tools/` files are read-only to the pipeline.

## Validation scope of this promotion

The promotion was validated with the offline regressions, an explicitly supplied
verified source cache, real pinned native flag witnesses, clean archive-only
SCOWL notice extraction, five cheap regenerated outputs (EN keys/surfaces and all
three frequency TSVs), and frozen checks of all nine outputs/notices/lock. The four
RU/ES output files were copied only after their frozen hashes matched. Seventeen
reviewed lexical function/class ASTs are unchanged by the path/config refactor.

**A complete cold rebuild and full RU/ES expansion were not rerun for this
promotion.** Historical reproducibility reports under `provenance/` describe the
reviewed source run; they are not evidence of a new cold run. Executing `verify`
validates artifact identities and supplied provenance, not proof that a particular
operator rebuilt them from scratch. Runtime format selection, APK data inclusion,
Android compatibility/performance and correction-quality gates remain separate.

## Reused build-directory boundary

Every public stage and worker entry checks the existing build tree before writes,
including leaf links such as logs, outputs and native executables. Pre-existing
symlinks escaping the selected physical build directory are rejected. The only
external link exceptions are the executable leaves `bin/host-tools/find` and
`bin/host-tools/grep`: they are read/execute-only, and host setup unlinks each
leaf before installing its verified GNU utility link. A redirected `host-tools`
directory or an output alias to those executable links is rejected. Internal
archive links remain allowed; archive extraction also uses Python's data filter.
The tree is checked again at stage and native/archive boundaries. Use one writer
per build directory: these pre-existing-tree checks are not a sandbox against
concurrent filesystem mutation.

# Offline lexicon prototype third-party notices

This prototype is not packaged in an APK. No upstream license is replaced by this document.
The original license and attribution files in `notices/` are part of the source package.
Every source URL and input SHA-256 is in `source-lock.json`; all archived members are
inventoried in `reports/archive-members.json`. Transformation source is in `scripts/`.

## Russian dictionary, separate permissive component

Source: [LibreOffice dictionaries, pinned revision](https://github.com/LibreOffice/dictionaries/tree/32b006a2c22a4ac7e8ed3f03346f7b3d85a970a4/ru_RU).
Only `ru_RU.aff`, `ru_RU.dic` and `README_ru_RU.txt` are used. Copyright
1997–2008 Alexander I. Lebedev; modification notice credits Laszlo Nemeth.
Original terms are preserved verbatim in `notices/RU-Lebedev.txt`.

`outputs/ru.words.txt` and `outputs/ru.surface-forms.txt` are **modified derived
versions**: finite Unicode suffix expansion, native Hunspell acceptance, length
limit 32 codepoints, NFC normalization, and deduplication. The keys additionally
use lowercase. The original copyright, conditions, disclaimer, and no-endorsement
condition must travel with redistributed source/binary-derived assets.

## Spanish dictionary, separate MPL component

Source: [LibreOffice dictionaries, pinned revision](https://github.com/LibreOffice/dictionaries/tree/32b006a2c22a4ac7e8ed3f03346f7b3d85a970a4/es).
The selected files are `es_ES.aff` and `es_ES.dic`. Santiago Bosio and the
contributors are attributed in `notices/ES-README.txt`.
Upstream explicitly offers GPL 3+, LGPL 3+, or MPL 1.1+; this prototype selects
the MPL 1.1 option for the separate Spanish asset. Original notices and text are
`notices/ES-LICENSE.md`, `notices/ES-README.txt`, and `notices/ES-MPL-1.1.txt`.

`outputs/es.words.txt` and `outputs/es.surface-forms.txt` are modified derived
versions: finite prefix/suffix/continuation expansion, maximum 32 codepoints,
native acceptance, NFC, unique sorting, and lowercase keys. Source line 92 has
trailing whitespace (`Araba `); it is trimmed to the lexical token `Araba`, with
the exact witness retained in `reports/es-whitespace-source-rows.json`.
Distribute the corresponding original dictionary, transformation sources and
license material alongside a future Spanish asset release; this prototype does
not relicense Spanish dictionary data as application code.

## English SCOWL component

Source: [en-wl/wordlist, pinned revision](https://github.com/en-wl/wordlist/tree/5ef55f9c42730ebe4394a78b77855468a6f15dd2).
Copyright Kevin Atkinson and contributing sources. The complete multi-source
notice is `notices/SCOWL-Copyright.txt`, not just a shorthand “MIT” label.
It includes WordNet and UKACD notices; UKACD contributes accent information.
The latter's copyright and full text are retained in the complete notice.

Selection is `perl mk-list --accents keep en_US 60` with default non-variant
categories (including the upstream implied English and special categories).
The upstream build creates word forms, including inflections and possessives.
`outputs/en.*.txt` converts ISO-8859-1 to UTF-8, applies NFC, limits to 32
codepoints, preserves case in the surface file, and creates unique lowercase
keys separately. No accent stripping or additional invented accent variants.

## FrequencyWords, separate CC-BY-SA 4.0 data component

Source: [Hermit Dave, FrequencyWords, pinned revision](https://github.com/hermitdave/FrequencyWords/tree/525f9b560de45753a5ea01069454e72e9aa541c6).
The RU/EN/ES `content/2018/*/*_50k.txt` lists are based on the OpenSubtitles2018
data identified by upstream. Preserve attribution to Hermit Dave/FrequencyWords
and that provenance link in `notices/FrequencyWords-README.md`.

The README explicitly licenses **content CC-BY-SA 4.0**, while the repository's
MIT `LICENSE` applies to code. Both original files are retained. The official
CC-BY-SA 4.0 text is `notices/CC-BY-SA-4.0.txt`; its exact source URL and digest
are locked separately as a versioned license document.

`outputs/frequency/{ru,en,es}.tsv` are separate modified data components under
CC-BY-SA 4.0: add a normalized key, preserve original word, rank, and count,
and sort rows. No frequencies are merged into the orthographic text assets.
Repeated normalized keys retain all source rows; no aggregate count or rank is
invented. Frequency probe results are diagnostics, not quality or holdout scores.

## Hunspell, host tool only

Source: [Hunspell, pinned revision](https://github.com/hunspell/hunspell/tree/e184e22c51fe213f4490e9b36998f0ad3e5e606b).
Native library and legacy `unmunch` are compiled locally, with no installation.
The offline wrapper `scripts/spell_oracle.cxx` is separately authored.
The original GPL/LGPL/MPL alternatives, MySpell attribution, and author list are
retained as `notices/Hunspell-*`. Hunspell is not linked or copied into any APK.
Its license does not replace the dictionary-data license or the frequency license.

All source archives remain available under `downloads/`. No source with an
unconfirmed license was substituted for any pinned source.

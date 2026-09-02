"""Derive RNK1 only from frozen inputs; never rebuild lexicons, indexes or frequency sources.

Invoke from the repository root with explicit source/index roots and a dedicated build child.
Outputs are immutable on rerun. The separate rank component remains CC-BY-SA-4.0 derived data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

SOURCE_MANIFEST_SHA = 'ec26c80edd28f2b42008a844c8b0ce83c11759386ccc9de591cb038a7a4f3c48'
PINNED = {
    'en': (121255, 272385, '2c81c9b4d317f802567297aecaee18927c756175b8f42bca7d01227bbfefbebc',
        '4f6c863c6a5bb88a077eff6cc108fd793a1dc8a681d2729941102d0e2d297ea4'),
    'es': (668267, 1250979, '7adab4a85ab5d4fbb378fb4e9c351dba51b17b4ff2ffec27ee24225a7a6d9681',
        'ce04ddffa33bc624a95cbbc50f955b1590aabf83a25b2c0d1a2dee7f2555fb78'),
    'ru': (1436553, 2255866, 'e96318206391f23d54384e4602f52c2cb31b16ed36a35657fbe467593183a82b',
        'b4fefb604d0ed4a181dc93e57c8d2417a0e929d3fa1512117d91d825ab60c69c'),
}
LANGUAGES = {'en': 'ENGLISH', 'es': 'SPANISH', 'ru': 'RUSSIAN'}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write(output, relative, data):
    destination = output / relative
    require(destination.is_relative_to(output), 'OUTPUT_SCOPE')
    for path in [destination, *destination.parents]:
        require(not path.is_symlink(), 'OUTPUT_SYMLINK')
        if path == output:
            break
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        require(destination.read_bytes() == data, 'OUTPUT_DRIFT')
    else:
        with destination.open('xb') as target:
            target.write(data)


def derive_ranks(word_lines, frequency_lines, word_count):
    """Assign ranks in canonical stream order; an absent frequency key is never an ordinal."""
    require(0 < word_count < 2**31 - 1, 'WORD_COUNT')
    frequency_lines = iter(frequency_lines)
    require(next(frequency_lines, '') == 'key\tsource_rank\tsource_word\tsource_count\n', 'FREQUENCY_HEADER')
    frequencies = {}
    for line in frequency_lines:
        fields = line.rstrip('\n').split('\t')
        require(len(fields) == 4 and fields[0] and fields[0] not in frequencies, 'FREQUENCY_ROW')
        rank = int(fields[1])
        require(0 < rank <= 50000, 'FREQUENCY_RANK')
        frequencies[fields[0]] = rank
    ranks = bytearray(struct.pack('<4sIIII', b'RNK1', word_count, 4, 0, 2147483647))
    count = 0
    previous = ''
    for count, line in enumerate(word_lines, 1):
        require(count <= word_count and line.endswith('\n'), 'WORD_COUNT_OR_LINE')
        word = line[:-1]
        require(word and word > previous and '\r' not in word, 'WORD_ORDER')
        ranks.extend(struct.pack('<I', frequencies.get(word, 2147483647)))
        previous = word
    require(count == word_count, 'WORD_COUNT')
    return bytes(ranks)


def identity(record):
    lines = ['RUNE_PACKED_LEXICON_1', record['language'], 'NFC_ROOT_LOWER_NFC_32_V1',
        str(record['words']), str(record['nodes']), str(record['maximum_frequency_rank'])]
    for asset in [record['trie'], record['lengths'], record['ranks']]:
        lines += [asset['path'], str(asset['bytes']), asset['sha256']]
    lines += [record['canonical_words_sha256'], SOURCE_MANIFEST_SHA, str(len(record['notices']))]
    for notice in record['notices']:
        lines += [notice['path'], str(notice['bytes']), notice['sha256']]
    return hashlib.sha256(('\n'.join(lines) + '\n').encode('ascii')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['source-root', 'index-root', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    require('..' not in output.parts, 'OUTPUT_SCOPE')
    build = Path.cwd().resolve() / 'build'
    require(output.is_relative_to(build) and output != build, 'DEDICATED_BUILD_OUTPUT_REQUIRED')
    for path in [output, *output.parents]:
        require(not path.is_symlink(), 'OUTPUT_SYMLINK')
        if path == build:
            break
    require(sha(args.source_root / 'output-manifest.json') == SOURCE_MANIFEST_SHA, 'SOURCE_MANIFEST_HASH')
    frozen = json.loads((args.source_root / 'output-manifest.json').read_text())
    words_meta = {entry['language']: entry['canonical_keys'] for entry in frozen['languages']}
    frequency_meta = {entry['language']: entry['data'] for entry in frozen['frequency']}
    notices = []
    for entry in frozen['notices']:
        require(sha(args.source_root / entry['path']) == entry['sha256'], 'NOTICE_HASH')
        notices.append({'path': 'smarttyping/lexicon/' + entry['path'], 'bytes': entry['bytes'], 'sha256': entry['sha256']})
    notices.sort(key=lambda entry: entry['path'])
    records = []
    evidence = []
    for language, (word_count, node_count, trie_sha, length_sha) in PINNED.items():
        trie = args.index_root / 'assets' / (language + '.trie')
        lengths = args.index_root / 'assets' / (language + '.trie.lengths')
        require(sha(trie) == trie_sha and sha(lengths) == length_sha, 'PINNED_ASSET_HASH')
        word_file = args.source_root / words_meta[language]['path']
        frequency_file = args.source_root / frequency_meta[language]['path']
        require(sha(word_file) == words_meta[language]['sha256'] and sha(frequency_file) == frequency_meta[language]['sha256'], 'FROZEN_WORD_FREQUENCY_HASH')
        with word_file.open(encoding='utf-8') as words, frequency_file.open(encoding='utf-8') as frequencies:
            rank_only = derive_ranks(words, frequencies, word_count)
        relative = Path('rank-assets') / (language + '.ranks')
        write(output, relative, rank_only)
        record = {'language': LANGUAGES[language], 'words': word_count, 'nodes': node_count, 'maximum_frequency_rank': 50000,
            'trie': {'path': f'smarttyping/lexicon/{language}.trie', 'bytes': trie.stat().st_size, 'sha256': trie_sha},
            'lengths': {'path': f'smarttyping/lexicon/{language}.trie.lengths', 'bytes': lengths.stat().st_size, 'sha256': length_sha},
            'ranks': {'path': f'smarttyping/lexicon/frequency/{language}.ranks', 'bytes': len(rank_only), 'sha256': hashlib.sha256(rank_only).hexdigest()},
            'canonical_words_sha256': words_meta[language]['sha256'], 'provenance_sha256': SOURCE_MANIFEST_SHA,
            'notices': notices, 'rank_component_license': 'CC-BY-SA-4.0',
            'frozen_frequency_sha256': frequency_meta[language]['sha256']}
        record['identity_sha256'] = identity(record)
        records.append(record)
        evidence.append({'language': language, 'derived_word_ranks': word_count, 'rnk_bytes': len(rank_only),
            'rnk_sha256': record['ranks']['sha256'], 'source': 'pinned_canonical_and_frequency_streams'})
        print(language, 'ranks_derived', word_count, 'rnk_bytes', len(rank_only), flush=True)

    def asset(value):
        return 'PackedAsset(' + json.dumps(value['path']) + ', ' + str(value['bytes']) + 'L, ' + json.dumps(value['sha256']) + ')'
    lines = ['package io.github.mesteriis.rune.keyboard.smarttyping.lexicon', '',
        'import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage', '',
        '/** Generated release metadata; orthographic and CC-BY-SA rank assets remain separate. */',
        'object FrozenPackedLexicons {']
    for record in records:
        lines += ['    val ' + record['language'] + ' = TrustedPackedLexicon(',
            '        KeyboardLanguage.' + record['language'] + ', ' + json.dumps(record['identity_sha256']) + ',',
            '        PackedLexiconManifest(',
            '            KeyboardLanguage.' + record['language'] + ', ' + str(record['words']) + ', ' + str(record['nodes']) + ',',
            *['            ' + asset(record[part]) + ',' for part in ['trie', 'lengths', 'ranks']],
            '            ' + json.dumps(record['canonical_words_sha256']) + ', ' + json.dumps(SOURCE_MANIFEST_SHA) + ',',
            '            listOf(', *['                ' + asset(notice) + ',' for notice in record['notices']],
            '            ),', '            maximumFrequencyRank = 50_000,', '        ),', '    )']
    lines += ['}', '']
    kotlin = Path('overlay/app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/FrozenPackedLexicons.kt')
    write(output, kotlin, '\n'.join(lines).encode())
    write(output, Path('asset-manifest.json'), (json.dumps(records, indent=2) + '\n').encode())
    write(output, Path('rank-derivation.json'), (json.dumps(evidence, indent=2) + '\n').encode())
    print('PASS immutable RNK1 derivation; no index/source regeneration; packaging measurement remains separate')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # No source word, exception payload or environment state in tool diagnostics.
        print('FAIL', type(error).__name__)
        raise SystemExit(2)

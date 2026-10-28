#!/usr/bin/env python3
"""Reproduce disclosed, label-free CC BY-SA regression inputs; never qualify spelling."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'tools/ci/product-replay-v1'
SEED = 'rune-product-replay-v1'
LANGUAGES = ('en', 'ru', 'es')
PATTERNS = {'en': '[a-z]{2,16}', 'ru': '[а-яё]{2,16}', 'es': '[a-záéíóúüñ]{2,16}'}
BUCKETS = ((2, 4), (5, 8), (9, 16))
PER_BUCKET = 60
PINNED = {'en': '5351ff405b1126ef555791dd4d9798a48e3e9a501a9fc481a9da957752cfb458',
    'ru': '6095f507cc167488ec66ada5a85ac50433503a08ad24a07c6eabdf54352c4e7f',
    'es': 'dcff3ad4316192f4dc4ff7d26e637c6ff314ef1ca0f3f720c5649018a71056c0'}


def sha(data): return hashlib.sha256(data).hexdigest()

def encoded(rows):
    return ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
        for row in rows).encode('utf-8')


def vocabulary(data, language):
    result, seen = [], set()
    for line, raw in enumerate(data.decode('utf-8').splitlines(), 1):
        source, count = raw.rsplit(' ', 1)
        if not count.isascii() or not count.isdecimal() or int(count) <= 0: raise ValueError('SOURCE_COUNT')
        word = unicodedata.normalize('NFC', source).casefold()
        if re.fullmatch(PATTERNS[language], word) and word not in seen:
            result.append({'word': word, 'sourceWord': source, 'sourceLine': line, 'frequency': int(count)})
            seen.add(word)
    return result


def variants(word):
    transposed = word
    for i in range(len(word) - 1):
        if word[i] != word[i + 1]:
            transposed = word[:i] + word[i + 1] + word[i] + word[i + 2:]
            break
    return (word, word[:len(word)//2] + word[len(word)//2 + 1:], transposed, word[0].upper() + word[1:])


def build(directory=DATA):
    directory = Path(directory)
    lock_path = directory / 'source-lock.json'
    lock_bytes = lock_path.read_bytes(); lock = json.loads(lock_bytes)
    if (lock.get('commit') != '525f9b560de45753a5ea01069454e72e9aa541c6' or
        lock.get('contentLicense') != 'CC-BY-SA-4.0' or lock.get('schemaVersion') != 1 or
        lock.get('repository') != 'hermitdave/FrequencyWords' or lock.get('author') != 'Hermit Dave' or
        lock.get('upstreamCorpus') != 'OpenSubtitles2018 via OPUS' or
        lock.get('readmeUrl') != 'https://github.com/hermitdave/FrequencyWords/blob/525f9b560de45753a5ea01069454e72e9aa541c6/README.md' or
        set(lock.get('files', {})) != set(LANGUAGES)):
        raise ValueError('SOURCE_LOCK')
    rows, origins = [], []
    for language in LANGUAGES:
        spec = lock['files'][language]
        if (spec.get('file') != 'sources/' + language + '_50k.txt' or spec.get('sha256') != PINNED[language] or
            spec.get('url') != f'https://raw.githubusercontent.com/hermitdave/FrequencyWords/525f9b560de45753a5ea01069454e72e9aa541c6/content/2018/{language}/{language}_50k.txt'):
            raise ValueError('SOURCE_LOCK_IDENTITY')
        source = (directory / spec['file']).read_bytes()
        if sha(source) != PINNED[language] or len(source) != spec['bytes']: raise ValueError('SOURCE_DRIFT')
        words = vocabulary(source, language)
        priority = lambda i: sha((SEED + ':' + language + ':' + words[i]['word']).encode('utf-8'))
        for low, high in BUCKETS:
            eligible = [i for i in range(3, len(words)) if low <= len(words[i]['word']) <= high]
            chosen = sorted(eligible, key=priority)[:PER_BUCKET]
            if len(chosen) != PER_BUCKET: raise ValueError('SOURCE_BUCKET_SHORT')
            for index in chosen:
                prefix = ' '.join(item['word'] for item in words[index-3:index])
                origin = words[index]
                group = len(origins)
                origins.append({'group': group, 'language': language, 'bucket': [low, high],
                    'target': origin, 'context': words[index-3:index]})
                for transform, typed in enumerate(variants(origin['word'])):
                    rows.append({'id': f'q7-v1-{len(rows):06d}', 'split': 'calibration',
                        'language': language, 'prefix': prefix, 'typed': typed})
    payloads = {'inputs.jsonl': encoded(rows), 'origins.jsonl': encoded(origins)}
    manifest = {'schemaVersion': 1, 'purpose': 'DISCLOSED_REGRESSION_NOT_QUALIFICATION',
        'contentLicense': 'CC-BY-SA-4.0', 'selectionSeed': SEED, 'perLengthBucket': PER_BUCKET,
        'buckets': [list(x) for x in BUCKETS], 'rows': len(rows), 'sourceGroups': len(origins),
        'languages': {lang: sum(row['language'] == lang for row in rows) for lang in LANGUAGES},
        'containsPersonalMessages': False, 'expectedLabels': False, 'modelCalls': 0,
        'selectionUsesModelOutput': False, 'sourceLockSha256': sha(lock_bytes),
        'generatorSha256': sha(Path(__file__).read_bytes()),
        'files': {name: sha(data) for name, data in payloads.items()},
        'transformOrder': ['source-surface', 'delete-middle-codepoint', 'first-unequal-adjacent-swap-or-identity', 'uppercase-initial'],
        'contextSemantics': 'previous three eligible frequency-list entries; synthetic, not a source sentence',
        'labelsSemantics': 'No surface is asserted correct or incorrect; frequency is not linguistic truth.',
        'freshHoldout': False}
    payloads['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    return payloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.check == (args.output is not None): parser.error('choose --check or a fresh --output')
    payloads = build()
    if args.check:
        for name, expected in payloads.items():
            if (DATA / name).read_bytes() != expected: raise ValueError('CORPUS_DRIFT:' + name)
        print('Q7 corpus byte-for-byte reproducible: 2160 rows, 540 source groups')
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, data in payloads.items(): (args.output / name).write_bytes(data)


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError) as error: sys.exit(str(error))

#!/usr/bin/env python3
"""Recover all matching article IDs for historical v2-v4 spelling rows."""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from check_historical_qualification_archives import load
from recover_early_ru_sources import archived_source
from recover_legacy_families import sha
from register_historical_qualification_controls import inputs

ROOT = Path(__file__).resolve().parents[2]


def selection_index(rows, generator, seed, language):
    selected = {}
    for row in rows:
        split = row['split']
        expected = row['expectedCandidate']
        word = row['candidates'][expected].removeprefix(' ')
        family = generator.family(word)
        prefix = row['prefix']
        identity = hashlib.sha256(
            f'{seed}:qualification:{language}:{family}:{prefix}'.encode()
        ).hexdigest()
        if (row['language'] != language or row['task'] != 'spelling'
                or split not in ('calibration', 'holdout')
                or row['family'] != family or row['template'] != f'{split}-wikipedia-{identity}'
                or identity in selected):
            raise ValueError('HISTORICAL_SPELLING_IDENTITY')
        selected[identity] = (row['id'], word, prefix, family)
    if len(selected) != len({value[0] for value in selected.values()}):
        raise ValueError('HISTORICAL_SPELLING_DUPLICATE_ID')
    return selected


def recover(version, language, shard):
    data = (inputs() if version == 'v2' else load())[version]
    manifest = json.loads(data['manifest.json'])
    paths = {}
    for suffix in ('generate_corpus.py', 'source-lock.json'):
        original, digest = next(
            (name, digest) for name, digest in manifest['sources'].items() if name.endswith('/' + suffix)
        )
        paths[suffix] = archived_source(ROOT, original, digest)
    lock = json.loads(paths['source-lock.json'].read_bytes())
    name = lock['languageFiles'][language]
    expected = lock['files'][name]
    rule = lock['articleSelection']
    if (rule != manifest['source']['articleSelection']
            or expected['sha256'] != manifest['source']['files'][name]
            or shard.stat().st_size != expected['bytes'] or sha(shard) != expected['sha256']):
        raise ValueError('HISTORICAL_SPELLING_SHARD')
    spec = importlib.util.spec_from_file_location('historical_spelling_generator', paths['generate_corpus.py'])
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    filename = f'spelling-{language}.jsonl'
    rows = [json.loads(line) for line in data[filename].splitlines()]
    # The v2 builder passes this literal rather than reading a corpusSeed field.
    seed = 3042026 if version == 'v2' else lock['corpusSeed']
    selected = selection_index(rows, generator, seed, language)
    known = {item[1] for item in selected.values()}
    articles = defaultdict(set)
    seen = set()
    eligible = 0
    import pyarrow.parquet as parquet

    for batch in parquet.ParquetFile(shard).iter_batches(columns=['id', 'text'], batch_size=128):
        for raw_id, content in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            article = str(raw_id)
            if not re.fullmatch(r'[0-9]+', article) or article in seen:
                raise ValueError('HISTORICAL_SPELLING_ARTICLE')
            seen.add(article)
            rank = int.from_bytes(hashlib.sha256(
                f"{rule['seed']}:{language}:{article}".encode()).digest()[:8], 'big')
            if rank % rule['modulus'] != rule['residue']:
                continue
            eligible += 1
            for candidate in generator.spelling_candidates(content or '', language, known, set(), seed):
                item = selected.get(candidate['selectionHash'])
                if item and (candidate['word'], candidate['prefix'], candidate['family']) == item[1:]:
                    articles[item[0]].add(article)
    counts = manifest['sourceReceipts'][language]
    if (len(seen) != counts['articlesScanned'] or eligible != counts['articlesSelected']
            or sha(shard) != expected['sha256']):
        raise ValueError('HISTORICAL_SPELLING_SCAN')
    missing = sorted({row['id'] for row in rows} - articles.keys())
    return {
        'version': version, 'language': language, 'sourceShardSha256': expected['sha256'],
        'sourceRevision': lock['parquetRevision'], 'sourcePath': expected['repositoryPath'],
        'rowsSha256': manifest['files'][filename],
        'generatorSha256': sha(paths['generate_corpus.py']), 'sourceLockSha256': sha(paths['source-lock.json']),
        'sourceArticlesScanned': len(seen), 'eligibleArticles': eligible,
        'rows': len(rows), 'missingRows': missing,
        'ambiguousRows': sum(len(ids) > 1 for ids in articles.values()),
        'matchingArticlesByRow': {row: sorted(ids, key=int) for row, ids in sorted(articles.items())},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=('v2', 'v3', 'v4'), required=True)
    parser.add_argument('--language', choices=('en', 'es', 'ru'), required=True)
    parser.add_argument('--shard', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = recover(args.version, args.language, args.shard)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n')
    return 1 if result['missingRows'] else 0


if __name__ == '__main__':
    raise SystemExit(main())

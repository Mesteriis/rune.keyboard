#!/usr/bin/env python3
"""Recover article metadata for registered punctuation and RU spelling examples."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import control_ledger
import holdout_ledger
from import_control_components import load_original
from import_early_ru_history import PREFIX
from recover_early_ru_sources import archived_source
from recover_historical_spelling_articles import recover as recover_spelling
from recover_historical_spelling_attribution import scan_article_metadata
from recover_legacy_families import sha
from recover_punctuation_articles import matches, selected_rows
from register_historical_qualification_controls import ROOT, inputs

HERE = Path(__file__).resolve().parent


def recover(version, language, shard):
    import pyarrow.parquet as parquet

    corpus = 'qualification-v2' if version == 'v2' else f'compact-{version}'
    data = inputs()[version]
    manifest = json.loads(data['manifest.json'])
    path, expected = next((p, h) for p, h in manifest['sources'].items()
                          if p.endswith('/source-lock.json'))
    lock = json.loads(archived_source(ROOT, path, expected).read_bytes())
    spec = lock['files'][lock['languageFiles'][language]]
    rule = lock['articleSelection']
    if (spec['bytes'] != shard.stat().st_size or spec['sha256'] != sha(shard)
            or spec['sha256'] != manifest['source']['files'][lock['languageFiles'][language]]
            or rule != manifest['source']['articleSelection']):
        raise ValueError('HISTORICAL_PUNCTUATION_ATTRIBUTION_SHARD')
    seed = 3042026 if version == 'v2' else lock['corpusSeed']
    filename = f'punctuation-{language}.jsonl'
    source_rows = [json.loads(line) for line in data[filename].splitlines()]
    selected = selected_rows(source_rows, seed)
    generator, generator_path = load_original(ROOT, manifest)
    source = parquet.ParquetFile(shard)
    articles_by_id = defaultdict(set)
    occurrences = scanned = eligible = 0
    for batch in source.iter_batches(columns=['id', 'text'], batch_size=128):
        for raw_id, content in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            article = str(raw_id)
            scanned += 1
            rank = int.from_bytes(hashlib.sha256(
                f"{rule['seed']}:{language}:{article}".encode()).digest()[:8], 'big')
            if rank % rule['modulus'] != rule['residue']:
                continue
            eligible += 1
            for item in matches(article, content, selected, generator, language, seed):
                articles_by_id[item['id']].add(article)
                occurrences += 1
    counts = manifest['sourceReceipts'][language]
    if (set(articles_by_id) != {r['id'] for r in source_rows}
            or scanned != counts['articlesScanned'] or eligible != counts['articlesSelected']):
        raise ValueError('HISTORICAL_PUNCTUATION_ATTRIBUTION_COVERAGE')
    pun_ids = set().union(*articles_by_id.values())
    control = control_ledger.load(HERE / 'control-ledger.json')
    entry = next(item for item in control['entries'] if item['id'] == f'{corpus}-punctuation-{language}')
    if (set(entry['articleKeys']) != {control_ledger.article_key({'article': article, 'language': language})
                                     for article in pun_ids}
            or entry['articleRecovery']['occurrences'] != occurrences):
        raise ValueError('HISTORICAL_PUNCTUATION_REGISTRY_DRIFT')
    report = dict(version=version, language=language, sourceShardSha256=spec['sha256'],
                  sourceRevision=lock['parquetRevision'], sourcePath=spec['repositoryPath'],
                  sourceColumns=source.schema_arrow.names, sourceLockSha256=expected,
                  generatorSha256=sha(generator_path), punctuationRowsSha256=manifest['files'][filename],
                  punctuationOccurrences=occurrences,
                  punctuation={row: sorted(ids, key=int) for row, ids in sorted(articles_by_id.items())})
    wanted = pun_ids
    if language == 'ru':
        spelling = recover_spelling(version, language, shard)
        ids = {article for group in spelling['matchingArticlesByRow'].values() for article in group}
        ledger = holdout_ledger.load_ledger(HERE / 'holdout-ledger.json')
        entry = next(item for item in ledger['entries'] if item['id'] == PREFIX + corpus)
        if spelling['missingRows'] or set(entry['keys']['article']) != holdout_ledger.keys_for(
                [{'article': article} for article in ids], 'article'):
            raise ValueError('HISTORICAL_RU_SPELLING_REGISTRY_DRIFT')
        report['ruSpellingRowsSha256'] = spelling['rowsSha256']
        report['ruSpelling'] = spelling['matchingArticlesByRow']
        wanted = wanted | ids
    report['articles'] = scan_article_metadata(source.iter_batches(columns=['id', 'title', 'url']), wanted, language)
    if sha(shard) != spec['sha256']:
        raise ValueError('HISTORICAL_PUNCTUATION_ATTRIBUTION_SHARD_DRIFT')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=('v2', 'v3', 'v4'), required=True)
    parser.add_argument('--language', choices=('en', 'es', 'ru'), required=True)
    parser.add_argument('--shard', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = recover(args.version, args.language, args.shard)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n')
    print(args.version, args.language, 'punctuation rows', len(report['punctuation']),
          'RU spelling rows', len(report.get('ruSpelling', {})), 'articles', len(report['articles']),
          'report SHA-256', sha(args.output), flush=True)


if __name__ == '__main__':
    main()

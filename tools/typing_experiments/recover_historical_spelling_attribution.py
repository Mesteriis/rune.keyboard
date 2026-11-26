#!/usr/bin/env python3
"""Index published article metadata from the pinned spelling-source shards."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from recover_legacy_families import sha
from register_historical_spelling_articles import MAPS, archives, digest


def scan_article_metadata(batches, wanted, language):
    found = {}
    for batch in batches:
        for raw_id, title, url in zip(*(batch.column(i).to_pylist() for i in range(3)), strict=True):
            article = str(raw_id)
            if article not in wanted:
                continue
            if (article in found or not isinstance(title, str) or not title.strip()
                    or not isinstance(url, str)):
                raise ValueError('HISTORICAL_ATTRIBUTION_ARTICLE')
            parsed = urlsplit(url)
            if (parsed.scheme != 'https' or parsed.netloc != f'{language}.wikipedia.org'
                    or not parsed.path.startswith('/wiki/') or parsed.query or parsed.fragment):
                raise ValueError('HISTORICAL_ATTRIBUTION_URL')
            found[article] = {'article': article, 'title': title, 'url': url}
    if set(found) != wanted:
        raise ValueError('HISTORICAL_ATTRIBUTION_COVERAGE')
    return [found[article] for article in sorted(found, key=int)]


def recover(version, language, shard):
    import pyarrow.parquet as parquet

    expected = MAPS[(version, language)]
    raw = (archives.ROOT / 'article-maps' / f'{version}-{language}.json').read_bytes()
    if digest(raw) != expected:
        raise ValueError('HISTORICAL_ATTRIBUTION_MAP')
    report = json.loads(raw)
    if sha(shard) != report['sourceShardSha256']:
        raise ValueError('HISTORICAL_ATTRIBUTION_SHARD')
    wanted = {article for group in report['matchingArticlesByRow'].values() for article in group}
    source = parquet.ParquetFile(shard)
    records = scan_article_metadata(source.iter_batches(columns=['id', 'title', 'url']), wanted, language)
    if sha(shard) != report['sourceShardSha256']:
        raise ValueError('HISTORICAL_ATTRIBUTION_SHARD_DRIFT')
    return records, {
        'language': language, 'version': version, 'articleMapSha256': expected,
        'sourceShardSha256': report['sourceShardSha256'], 'sourcePath': report['sourcePath'],
        'sourceRevision': report['sourceRevision'], 'sourceColumns': source.schema_arrow.names,
        'articles': len(records),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=('v2', 'v3', 'v4'), required=True)
    parser.add_argument('--language', choices=('en', 'es'), required=True)
    parser.add_argument('--shard', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    records, details = recover(args.version, args.language, args.shard)
    with args.output.open('x', encoding='utf-8') as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
    details['outputSha256'] = sha(args.output)
    print(json.dumps(details, sort_keys=True))


if __name__ == '__main__':
    main()
